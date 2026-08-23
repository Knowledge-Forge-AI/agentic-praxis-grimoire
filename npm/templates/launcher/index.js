#!/usr/bin/env node
"use strict";

const childProcess = require("node:child_process");
const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const MANIFEST_SCHEMA = "apg.binary-manifest/v1";
const BUILD_INFO_SCHEMA = "apg.build-info/v1";
const MODULE_PATH = "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire";
const BUILD_FLAGS = Object.freeze(["CGO_ENABLED=0", "-trimpath", "-buildvcs=false", "-buildid="]);
const BINARY_BASENAME = "apgr";
const TARGETS = Object.freeze({
  "darwin/arm64": Object.freeze({
    packageName: "@knowledge-forge-ai/apgr-darwin-arm64",
    os: "darwin",
    cpu: "arm64",
    goTarget: "darwin/arm64",
  }),
  "linux/arm64": Object.freeze({
    packageName: "@knowledge-forge-ai/apgr-linux-arm64",
    os: "linux",
    cpu: "arm64",
    goTarget: "linux/arm64",
  }),
  "linux/x64": Object.freeze({
    packageName: "@knowledge-forge-ai/apgr-linux-x64",
    os: "linux",
    cpu: "x64",
    goTarget: "linux/amd64",
  }),
});

function fail(message) {
  throw new Error(message);
}
function stableJson(value) {
  if (Array.isArray(value)) {
    return value.map(stableJson);
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value).sort().map((key) => [key, stableJson(value[key])]),
    );
  }
  return value;
}
function readDirectJson(file, label, canonical = false) {
  let metadata;
  try {
    metadata = fs.lstatSync(file);
  } catch (_error) {
    fail(`${label} is unavailable`);
  }
  if (!metadata.isFile() || metadata.isSymbolicLink()) {
    fail(`${label} is not a direct regular file`);
  }
  let text;
  try {
    text = fs.readFileSync(file, "utf8");
  } catch (_error) {
    fail(`${label} cannot be read`);
  }
  let value;
  try {
    value = JSON.parse(text);
  } catch (_error) {
    fail(`${label} is malformed`);
  }
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    fail(`${label} is not a JSON object`);
  }
  if (canonical && text !== `${JSON.stringify(stableJson(value))}\n`) {
    fail(`${label} is not canonical JSON`);
  }
  return value;
}
function selectTarget(platform = process.platform, architecture = process.arch) {
  const key = `${platform}/${architecture}`;
  const target = TARGETS[key];
  if (!target) {
    fail(`unsupported platform: ${key}`);
  }
  return { ...target, runtimeTarget: key, target: target.goTarget };
}
function manifestTarget(manifest) {
  const value = manifest.target;
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return undefined;
  }
  if (typeof value.go_target !== "string" || typeof value.goos !== "string" || typeof value.goarch !== "string") {
    return undefined;
  }
  return value.go_target;
}
function validateManifest(manifest, target, expectedVersion, expectedCorpus, binary) {
  const expectedKeys = new Set([
    "binary_name",
    "build_flags",
    "build_identity",
    "build_info_schema",
    "corpus_fingerprint",
    "module_path",
    "schema_version",
    "sha256",
    "size_bytes",
    "target",
    "version",
  ]);
  const actualKeys = Object.keys(manifest);
  if (actualKeys.length !== expectedKeys.size || actualKeys.some((key) => !expectedKeys.has(key))) {
    fail("binary manifest fields are not canonical");
  }
  if (manifest.schema_version !== MANIFEST_SCHEMA) {
    fail("binary manifest schema is unsupported");
  }
  if (manifest.version !== expectedVersion) {
    fail("binary manifest version does not match launcher");
  }
  if (manifestTarget(manifest) !== target.target) {
    fail("binary manifest target does not match current platform");
  }
  const expectedMapping = {
    go_target: target.target,
    goos: target.os,
    goarch: target.cpu === "x64" ? "amd64" : target.cpu,
    python_platform: target.target === "darwin/arm64" ? "macosx_11_0_arm64" :
      target.target === "linux/amd64" ? "manylinux_2_17_x86_64" : "manylinux_2_17_aarch64",
    npm_package: target.packageName,
    npm_os: target.os,
    npm_cpu: target.cpu,
  };
  const observedMapping = manifest.target;
  const observedKeys = Object.keys(observedMapping);
  const expectedTargetKeys = Object.keys(expectedMapping);
  if (observedKeys.length !== expectedTargetKeys.length ||
      expectedTargetKeys.some((key) => !observedKeys.includes(key))) {
    fail("binary manifest target mapping is not canonical");
  }
  for (const key of Object.keys(expectedMapping)) {
    if (observedMapping[key] !== expectedMapping[key]) {
      fail("binary manifest target mapping does not match package contract");
    }
  }
  if (manifest.module_path !== MODULE_PATH) {
    fail("binary manifest module identity is wrong");
  }
  if (manifest.build_info_schema !== BUILD_INFO_SCHEMA) {
    fail("binary manifest build-info schema is wrong");
  }
  if (!Array.isArray(manifest.build_flags) ||
      manifest.build_flags.length !== BUILD_FLAGS.length ||
      manifest.build_flags.some((value, index) => value !== BUILD_FLAGS[index])) {
    fail("binary manifest build flags are wrong");
  }
  const identity = manifest.build_identity;
  const identityKeys = identity && typeof identity === "object" && !Array.isArray(identity)
    ? Object.keys(identity)
    : [];
  const expectedIdentityKeys = ["corpus_fingerprint", "schema_version", "target", "version"];
  if (identityKeys.length !== expectedIdentityKeys.length ||
      expectedIdentityKeys.some((key) => !identityKeys.includes(key)) ||
      identity.corpus_fingerprint !== expectedCorpus ||
      identity.schema_version !== BUILD_INFO_SCHEMA ||
      identity.target !== target.target ||
      identity.version !== expectedVersion) {
    fail("binary manifest build identity is inconsistent");
  }
  const corpus = manifest.corpus_fingerprint;
  if (typeof corpus !== "string" || corpus !== expectedCorpus) {
    fail("binary manifest corpus fingerprint does not match package identity");
  }
  const basename = manifest.binary_name;
  if (basename !== BINARY_BASENAME) {
    fail("binary manifest basename is not apgr");
  }
  const size = manifest.size_bytes;
  if (!Number.isSafeInteger(size) || size < 0) {
    fail("binary manifest size is invalid");
  }
  const digest = manifest.sha256;
  if (typeof digest !== "string" || !/^[0-9a-f]{64}$/.test(digest)) {
    fail("binary manifest SHA-256 is invalid");
  }
  let metadata;
  try {
    metadata = fs.lstatSync(binary);
  } catch (_error) {
    fail("packaged Go binary is unavailable");
  }
  if (
    !metadata.isFile() ||
    metadata.isSymbolicLink() ||
    (metadata.mode & 0o111) === 0
  ) {
    fail("packaged Go binary is not a direct executable");
  }
  let contents;
  try {
    contents = fs.readFileSync(binary);
  } catch (_error) {
    fail("packaged Go binary cannot be read");
  }
  if (contents.length !== size) {
    fail("packaged Go binary size does not match manifest");
  }
  const actual = crypto.createHash("sha256").update(contents).digest("hex");
  if (actual !== digest) {
    fail("packaged Go binary SHA-256 does not match manifest");
  }
}
function launch(argumentsList = process.argv.slice(2), overrides = {}) {
  const currentProcess = overrides.process ?? process;
  const target = selectTarget(
    overrides.platform ?? currentProcess.platform,
    overrides.architecture ?? currentProcess.arch,
  );
  const launcherRoot = overrides.launcherRoot ?? __dirname;
  const launcherPackage = overrides.launcherPackage ??
    readDirectJson(path.join(launcherRoot, "package.json"), "launcher package metadata");
  const expectedVersion = launcherPackage.version;
  const contract = launcherPackage.apg;
  if (typeof expectedVersion !== "string" || expectedVersion.length === 0) {
    fail("launcher package version is missing");
  }
  if (!contract || typeof contract !== "object") {
    fail("launcher package identity is missing");
  }
  if (contract.binary_manifest_schema !== MANIFEST_SCHEMA) {
    fail("launcher package manifest schema is unsupported");
  }
  const expectedCorpus = contract.corpus_fingerprint;
  if (typeof expectedCorpus !== "string" || !/^[0-9a-f]{64}$/.test(expectedCorpus)) {
    fail("launcher package corpus fingerprint is invalid");
  }
  const resolvePackage = overrides.resolvePackage ??
    ((name) => require.resolve(`${name}/package.json`, { paths: [launcherRoot] }));
  let platformMetadataPath;
  try {
    platformMetadataPath = resolvePackage(target.packageName);
  } catch (_error) {
    fail(`platform package ${target.packageName} is unavailable`);
  }
  const platformRoot = path.dirname(platformMetadataPath);
  const platformPackage = readDirectJson(platformMetadataPath, "platform package metadata");
  if (platformPackage.name !== target.packageName || platformPackage.version !== expectedVersion) {
    fail("platform package identity does not match launcher");
  }
  const platformContract = platformPackage.apg;
  if (!platformContract || platformContract.target !== target.target) {
    fail("platform package target does not match current platform");
  }
  if (platformContract.corpus_fingerprint !== expectedCorpus) {
    fail("platform package corpus does not match launcher");
  }
  const binary = path.join(platformRoot, "bin", BINARY_BASENAME);
  const manifest = readDirectJson(
    path.join(platformRoot, "bin", "apgr.binary-manifest.json"),
    "binary manifest",
    true,
  );
  validateManifest(manifest, target, expectedVersion, expectedCorpus, binary);
  const child = (overrides.childProcess ?? childProcess).spawnSync(
    binary,
    Array.from(argumentsList),
    { shell: false, stdio: "inherit" },
  );
  if (child.error) {
    fail("packaged Go binary could not be launched");
  }
  if (child.signal) {
    const signalNumber = os.constants.signals[child.signal];
    if (signalNumber !== undefined && typeof currentProcess.kill === "function") {
      currentProcess.kill(currentProcess.pid, child.signal);
      return 128 + signalNumber;
    }
    return 1;
  }
  if (!Number.isInteger(child.status)) {
    fail("packaged Go binary returned no status");
  }
  return child.status;
}
function main() {
  try {
    return launch();
  } catch (error) {
    const message = error instanceof Error ? error.message : "launcher failed";
    process.stderr.write(`apgr: ${message}\n`);
    return 1;
  }
}

module.exports = { BINARY_BASENAME, MANIFEST_SCHEMA, TARGETS, launch, main, selectTarget, validateManifest };

if (require.main === module) {
  process.exitCode = main();
}
