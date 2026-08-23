"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const launcher = require("../templates/launcher/index.js");

const CORPUS = "a".repeat(64);

function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonical(value[key])]));
  }
  return value;
}

function fixture(overrides = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "apgr-npm-launcher-"));
  const launcherRoot = path.join(root, "launcher");
  const platformRoot = path.join(root, "platform");
  const binRoot = path.join(platformRoot, "bin");
  fs.mkdirSync(binRoot, { recursive: true });
  const target = overrides.target ?? "linux/amd64";
  const version = overrides.version ?? "0.7.0";
  const binary = Buffer.from("#!/bin/sh\nexit 0\n");
  const binaryPath = path.join(binRoot, "apgr");
  fs.writeFileSync(binaryPath, binary, { mode: 0o755 });
  const manifest = {
    schema_version: launcher.MANIFEST_SCHEMA,
    version,
    target: {
      go_target: target,
      goos: "linux",
      goarch: "amd64",
      python_platform: "manylinux_2_17_x86_64",
      npm_package: "@knowledge-forge-ai/apgr-linux-x64",
      npm_os: "linux",
      npm_cpu: "x64",
    },
    binary_name: "apgr",
    size_bytes: binary.length,
    sha256: crypto.createHash("sha256").update(binary).digest("hex"),
    build_identity: {
      corpus_fingerprint: overrides.corpus ?? CORPUS,
      schema_version: "apg.build-info/v1",
      target,
      version,
    },
    corpus_fingerprint: overrides.corpus ?? CORPUS,
    module_path: "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire",
    build_info_schema: "apg.build-info/v1",
    build_flags: ["CGO_ENABLED=0", "-trimpath", "-buildvcs=false", "-buildid="],
  };
  if (overrides.manifest) Object.assign(manifest, overrides.manifest);
  fs.writeFileSync(
    path.join(binRoot, "apgr.binary-manifest.json"),
    `${JSON.stringify(canonical(manifest))}\n`,
  );
  fs.mkdirSync(launcherRoot, { recursive: true });
  fs.writeFileSync(
    path.join(launcherRoot, "package.json"),
    `${JSON.stringify({
      name: "@knowledge-forge-ai/apgr",
      version,
      apg: {
        binary_manifest_schema: launcher.MANIFEST_SCHEMA,
        corpus_fingerprint: overrides.launcherCorpus ?? CORPUS,
      },
    })}\n`,
  );
  fs.writeFileSync(
    path.join(platformRoot, "package.json"),
    `${JSON.stringify({
      name: "@knowledge-forge-ai/apgr-linux-x64",
      version,
      os: ["linux"],
      cpu: ["x64"],
      apg: { target, corpus_fingerprint: overrides.platformCorpus ?? CORPUS },
    })}\n`,
  );
  return { launcherRoot, platformRoot, binaryPath };
}

function runtime(fixtureRoot, childProcess, extra = {}) {
  return {
    platform: "linux",
    architecture: "x64",
    launcherRoot: fixtureRoot.launcherRoot,
    resolvePackage: () => path.join(fixtureRoot.platformRoot, "package.json"),
    childProcess,
    process: { pid: 42, kill: extra.kill ?? (() => {}) },
  };
}

test("maps supported targets and refuses unsupported platforms", () => {
  assert.equal(launcher.selectTarget("darwin", "arm64").target, "darwin/arm64");
  assert.equal(launcher.selectTarget("linux", "x64").target, "linux/amd64");
  assert.throws(() => launcher.selectTarget("freebsd", "x64"), /unsupported platform/);
});

test("validates exact argv, shell false, inherited stdio, and status", () => {
  const root = fixture();
  let observed;
  const childProcess = {
    spawnSync(binary, argumentsList, options) {
      observed = { binary, argumentsList, options };
      return { status: 23, signal: null, error: null };
    },
  };
  const status = launcher.launch(["--literal", "$(touch nope)", "a b"], runtime(root, childProcess));
  assert.equal(status, 23);
  assert.deepEqual(observed.argumentsList, ["--literal", "$(touch nope)", "a b"]);
  assert.equal(observed.binary, root.binaryPath);
  assert.deepEqual(observed.options, { shell: false, stdio: "inherit" });
});

test("propagates a child signal through the parent process boundary", () => {
  const root = fixture();
  let killed;
  const childProcess = { spawnSync: () => ({ status: null, signal: "SIGTERM", error: null }) };
  const status = launcher.launch(
    [],
    runtime(root, childProcess, { kill: (pid, signal) => { killed = { pid, signal }; } }),
  );
  assert.deepEqual(killed, { pid: 42, signal: "SIGTERM" });
  assert.equal(status, 128 + 15);
});

test("fails closed on manifest, package, and binary tamper", () => {
  const badManifest = fixture({ manifest: { sha256: "0".repeat(64) } });
  assert.throws(
    () => launcher.launch([], runtime(badManifest, { spawnSync: () => ({ status: 0 }) })),
    /SHA-256/,
  );
  const badVersion = fixture({ manifest: { version: "9.9.9" } });
  assert.throws(
    () => launcher.launch([], runtime(badVersion, { spawnSync: () => ({ status: 0 }) })),
    /manifest version/,
  );
  const badCorpus = fixture({ launcherCorpus: "b".repeat(64) });
  assert.throws(
    () => launcher.launch([], runtime(badCorpus, { spawnSync: () => ({ status: 0 }) })),
    /corpus/,
  );
  fs.appendFileSync(badCorpus.binaryPath, "tamper");
  assert.throws(
    () => launcher.launch([], runtime(badCorpus, { spawnSync: () => ({ status: 0 }) })),
    /corpus|size|SHA-256/,
  );
  const extraTargetField = fixture();
  const manifestPath = path.join(extraTargetField.platformRoot, "bin", "apgr.binary-manifest.json");
  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  manifest.target.unexpected = "rejected";
  fs.writeFileSync(manifestPath, `${JSON.stringify(canonical(manifest))}\n`);
  assert.throws(
    () => launcher.launch([], runtime(extraTargetField, { spawnSync: () => ({ status: 0 }) })),
    /target mapping/,
  );
});
