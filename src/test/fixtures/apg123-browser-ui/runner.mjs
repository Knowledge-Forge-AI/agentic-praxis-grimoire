#!/usr/bin/env node
/**
 * APG123 Maintained Browser UI Harness Runner.
 * Executes synthetic scenarios on real Playwright Chromium, Firefox, and WebKit runtimes.
 * Enforces zero arbitrary network access, ephemeral loopback serving, and scratch-bounded state.
 */

import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { runPlaywrightSupervisor } from './supervisor_runner.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Module-level engine and assertion handles initialized after custody verification
let chromium;
let firefox;
let webkit;
let expect;
let BROWSER_ENGINES = {};
let scratchDir;
let artifactsDir;

function findRepoRoot() {
  if (process.env.APG_REPOSITORY_ROOT) {
    return path.resolve(process.env.APG_REPOSITORY_ROOT);
  }
  let curr = __dirname;
  while (curr && curr !== path.dirname(curr)) {
    if (fs.existsSync(path.join(curr, '.git')) || fs.existsSync(path.join(curr, 'AGENTS.md'))) {
      return curr;
    }
    curr = path.dirname(curr);
  }
  curr = process.cwd();
  while (curr && curr !== path.dirname(curr)) {
    if (fs.existsSync(path.join(curr, '.git')) || fs.existsSync(path.join(curr, 'AGENTS.md'))) {
      return curr;
    }
    curr = path.dirname(curr);
  }
  return null;
}

function validateInsideScratch(targetPath, scratchReal, label) {
  const rel = path.relative(scratchReal, targetPath);
  if (rel.startsWith('..') || path.isAbsolute(rel) || rel === '') {
    throw new Error(`${label} destination escapes scratch directory: ${targetPath}`);
  }

  let curr = targetPath;
  while (curr && curr !== scratchReal && curr !== path.dirname(curr)) {
    let stat = null;
    try {
      stat = fs.lstatSync(curr);
    } catch (err) {
      if (err.code !== 'ENOENT') {
        throw err;
      }
    }
    if (stat) {
      if (stat.isSymbolicLink()) {
        throw new Error(`${label} path contains symlink: ${curr}`);
      }
      try {
        const real = fs.realpathSync(curr);
        if (real !== curr) {
          throw new Error(`${label} path contains resolved symlink: ${curr} -> ${real}`);
        }
      } catch (err) {
        throw new Error(`${label} path could not be resolved: ${err.message}`);
      }
    }
    curr = path.dirname(curr);
  }
}

export function validateRunnerCustody(cliArgs) {
  const getArg = (flag) => {
    const index = cliArgs.indexOf(flag);
    if (index !== -1 && index + 1 < cliArgs.length) {
      return cliArgs[index + 1];
    }
    return null;
  };

  const rawScratch = getArg('--scratch');
  if (!rawScratch || !rawScratch.trim()) {
    throw new Error('Explicit --scratch directory is required');
  }
  const scratchTrimmed = rawScratch.trim();
  if (!path.isAbsolute(scratchTrimmed)) {
    throw new Error(`Scratch directory must be an absolute path: ${scratchTrimmed}`);
  }
  if (!fs.existsSync(scratchTrimmed)) {
    throw new Error(`Scratch directory does not exist: ${scratchTrimmed}`);
  }
  const scratchStat = fs.lstatSync(scratchTrimmed);
  if (scratchStat.isSymbolicLink()) {
    throw new Error(`Scratch directory must not be a symlink: ${scratchTrimmed}`);
  }
  if (!scratchStat.isDirectory()) {
    throw new Error(`Scratch path must be a directory: ${scratchTrimmed}`);
  }

  let scratchReal;
  try {
    scratchReal = fs.realpathSync(scratchTrimmed);
  } catch (err) {
    throw new Error(`Scratch directory could not be resolved: ${err.message}`);
  }
  if (scratchReal !== scratchTrimmed) {
    throw new Error(`Scratch directory must be a direct path without symlinks: ${scratchTrimmed} -> ${scratchReal}`);
  }

  if (typeof process.getuid === 'function') {
    if (scratchStat.uid !== process.getuid()) {
      throw new Error(`Scratch directory must be owned by caller (uid ${process.getuid()}), got uid ${scratchStat.uid}`);
    }
  }

  const mode = scratchStat.mode & 0o777;
  if (mode !== 0o700) {
    throw new Error(`Scratch directory must be mode 0700, got: 0${mode.toString(8)}`);
  }

  const repoRoot = findRepoRoot();
  if (repoRoot) {
    let repoReal;
    try {
      repoReal = fs.realpathSync(repoRoot);
    } catch {
      repoReal = path.resolve(repoRoot);
    }
    if (scratchReal === repoReal ||
        scratchReal.startsWith(repoReal + path.sep) ||
        repoReal.startsWith(scratchReal + path.sep)) {
      throw new Error(`Scratch directory must be strictly outside repository checkout: ${scratchTrimmed}`);
    }
  }

  const rawReceipt = getArg('--receipt') || path.join(scratchReal, 'receipt.json');
  const receiptPath = path.resolve(rawReceipt);
  validateInsideScratch(receiptPath, scratchReal, 'Receipt');

  const rawArtifacts = getArg('--artifacts') || path.join(scratchReal, 'artifacts');
  const artifactsDir = path.resolve(rawArtifacts);
  validateInsideScratch(artifactsDir, scratchReal, 'Artifacts');

  const requestedBrowsersRaw = getArg('--browsers') || 'chromium,firefox,webkit';
  const requestedBrowsers = requestedBrowsersRaw.split(',').map(s => s.trim().toLowerCase()).filter(Boolean);
  const requestedGroup = (getArg('--group') || 'all').toLowerCase();
  const filterScenariosRaw = getArg('--scenarios') || '';
  let scenarioFilter = null;
  if (filterScenariosRaw) {
    const rawFilterList = filterScenariosRaw.split(',').map(s => s.trim().toUpperCase()).filter(Boolean);
    const seenFilter = new Set();
    for (const scId of rawFilterList) {
      if (seenFilter.has(scId)) {
        throw new Error(`Duplicate scenario ID in filter: ${scId}`);
      }
      seenFilter.add(scId);
    }
    scenarioFilter = seenFilter;
  }
  const rawTable = getArg('--table');
  const tablePath = rawTable ? path.resolve(rawTable) : path.join(__dirname, 'family_table.json');
  const rawRegister = getArg('--register');
  const registerPath = rawRegister ? path.resolve(rawRegister) : path.join(__dirname, 'scenarios.json');

  return {
    scratchDir: scratchReal,
    receiptPath,
    artifactsDir,
    requestedBrowsers,
    requestedGroup,
    scenarioFilter,
    tablePath,
    registerPath,
  };
}

const MAX_CAUSE_DEPTH = 5;

export function sanitizeDiagnosticText(text, maxLen = 2000) {
  if (text === null || text === undefined) return '';
  let str = typeof text === 'string' ? text : String(text);
  if (process.env.HOME) {
    str = str.replaceAll(process.env.HOME, '<HOME>');
  }
  if (process.env.APG_PLAYWRIGHT_OWNED_SCRATCH_ROOT) {
    str = str.replaceAll(process.env.APG_PLAYWRIGHT_OWNED_SCRATCH_ROOT, '<SCRATCH_ROOT>');
  }
  // URL userinfo
  str = str.replace(/([a-zA-Z][a-zA-Z0-9+.-]*:\/\/)([^/\s@]+)@/g, '$1<REDACTED>@');
  // Bearer tokens
  str = str.replace(/\b(bearer\s+)[A-Za-z0-9_\-\.=]+/gi, '$1<REDACTED>');
  // auth/token/password assignments (quoted)
  str = str.replace(/\b([a-z0-9_-]*(?:auth(?!ority)(?:orization)?|token|password|passwd|secret|credential)[a-z0-9_-]*\s*[:=]\s*)(["'])(?:(?=(\\?))\3.)*?\2/gi, '$1$2<REDACTED>$2');
  // auth/token/password assignments (unquoted)
  str = str.replace(/\b([a-z0-9_-]*(?:auth(?!ority)(?:orization)?|token|password|passwd|secret|credential)[a-z0-9_-]*\s*[:=]\s*)(?!["'])[^\s,;&]+/gi, '$1<REDACTED>');

  if (str.length > maxLen) {
    str = str.slice(0, maxLen) + '...[truncated]';
  }
  return str;
}

export function sanitizeCause(cause, depth = 0, seen = new Set()) {
  if (!cause) return null;
  if (depth >= MAX_CAUSE_DEPTH) {
    return '[MaxCauseDepthExceeded]';
  }
  if (typeof cause === 'object' && cause !== null) {
    if (seen.has(cause)) {
      return '[Circular]';
    }
    seen.add(cause);
  }
  try {
    if (cause instanceof Error || (typeof cause === 'object' && cause !== null && 'message' in cause)) {
      const errClass = cause.name || (cause.constructor && cause.constructor.name) || 'Error';
      const msg = sanitizeDiagnosticText(cause.message);
      let nestedCause = null;
      if (cause.cause) {
        if (depth + 1 >= MAX_CAUSE_DEPTH) {
          nestedCause = '[MaxCauseDepthExceeded]';
        } else {
          nestedCause = sanitizeCause(cause.cause, depth + 1, seen);
        }
      }
      return {
        class: errClass,
        message: msg,
        cause: nestedCause,
      };
    }
    return sanitizeDiagnosticText(String(cause), 1000);
  } catch {
    return '[UnserializableCause]';
  }
}

export function sanitizeError(err) {
  if (!err) return { class: 'Error', message: 'Unknown error', cause: null };
  const errClass = err.name || (err.constructor && err.constructor.name) || 'Error';
  const message = sanitizeDiagnosticText(err.message || String(err));
  const seen = new Set();
  if (typeof err === 'object' && err !== null) {
    seen.add(err);
  }
  let cause = null;
  try {
    cause = err.cause ? sanitizeCause(err.cause, 0, seen) : null;
  } catch {
    cause = '[UnserializableCause]';
  }
  return {
    class: errClass,
    message,
    cause,
  };
}

// Load scenario register and family table
const scenariosManifest = JSON.parse(fs.readFileSync(path.join(__dirname, 'scenarios.json'), 'utf-8'));
const allScenarios = scenariosManifest.scenarios;
const familyTable = JSON.parse(fs.readFileSync(path.join(__dirname, 'family_table.json'), 'utf-8'));

export function validateFamilyTable(table) {
  if (!table || typeof table !== 'object' || Array.isArray(table)) {
    throw new Error('Family table must be a valid JSON object');
  }
  if (table.schema_version !== '1.0.0') {
    throw new Error(`Unsupported family table schema_version: ${table.schema_version}`);
  }
  if (!table.authority || typeof table.authority !== 'string') {
    throw new Error('Family table missing valid authority');
  }
  if (!table.families || !Array.isArray(table.families)) {
    throw new Error('Family table families must be an array');
  }

  const seenFamilies = new Set();
  const familyMap = new Map();
  const groupToFamily = new Map();

  for (const fam of table.families) {
    if (!fam || typeof fam !== 'object' || Array.isArray(fam)) {
      throw new Error('Family table family row must be an object');
    }
    const fId = fam.id;
    if (!fId || typeof fId !== 'string') {
      throw new Error('Family table family row missing valid identifier');
    }
    if (seenFamilies.has(fId)) {
      throw new Error(`Duplicate family registration in family table: ${fId}`);
    }
    seenFamilies.add(fId);

    if (!fam.authority || typeof fam.authority !== 'string') {
      throw new Error(`Family table missing valid authority for family: ${fId}`);
    }
    familyMap.set(fId, fam);

    if (!Array.isArray(fam.groups)) {
      throw new Error("Family groups must be an array");
    }
    if (Array.isArray(fam.groups)) {
      for (const grp of fam.groups) {
        if (!grp || typeof grp !== 'string') {
          throw new Error(`Invalid group name in family ${fId}`);
        }
        if (groupToFamily.has(grp)) {
          throw new Error(`Duplicate or ambiguous group registration in family table: ${grp}`);
        }
        groupToFamily.set(grp, fId);
      }
    }
  }

  if (table.supported_mixes !== undefined) {
    if (!Array.isArray(table.supported_mixes)) {
      throw new Error('Family table supported_mixes must be an array');
    }
    const seenMixSets = new Set();
    for (const mix of table.supported_mixes) {
      if (!mix || typeof mix !== 'object' || Array.isArray(mix)) {
        throw new Error('Invalid supported_mixes row type: must be an object');
      }
      if (!mix.authority || typeof mix.authority !== 'string') {
        throw new Error('supported_mixes row missing valid authority');
      }
      if (!Array.isArray(mix.families) || mix.families.length === 0) {
        throw new Error('supported_mixes row families must be a non-empty array');
      }
      const mixFamilySeen = new Set();
      for (const mf of mix.families) {
        if (!mf || typeof mf !== 'string') {
          throw new Error(`supported_mixes contains invalid family identifier: ${mf}`);
        }
        if (!seenFamilies.has(mf)) {
          throw new Error(`supported_mixes references unknown family: ${mf}`);
        }
        if (mixFamilySeen.has(mf)) {
          throw new Error(`Duplicate family in supported_mixes row: ${mf}`);
        }
        mixFamilySeen.add(mf);
      }
      if (mixFamilySeen.size === 1) {
        const singleFam = Array.from(mixFamilySeen)[0];
        throw new Error(`Ambiguous family registration: singleton mix for family '${singleFam}' registered in supported_mixes`);
      }
      const mixKey = Array.from(mixFamilySeen).sort().join('::');
      if (seenMixSets.has(mixKey)) {
        throw new Error(`Duplicate mix registration in family table: ${Array.from(mixFamilySeen).sort().join(', ')}`);
      }
      seenMixSets.add(mixKey);
    }
  }

  if (!Array.isArray(table.entries)) {
    throw new Error('Family table entries must be an array');
  }

  const seenIds = new Set();
  for (const entry of table.entries) {
    if (!entry || typeof entry !== 'object') {
      throw new Error('Invalid family table entry');
    }
    const { id, group, family } = entry;
    if (!id || typeof id !== 'string') {
      throw new Error('Family table entry missing valid id');
    }
    if (seenIds.has(id)) {
      throw new Error(`Duplicate scenario ID in family table: ${id}`);
    }
    seenIds.add(id);

    if (!family || !seenFamilies.has(family)) {
      throw new Error(`Unknown family in family table for scenario ${id}: ${family}`);
    }
    if (!group || !groupToFamily.has(group)) {
      throw new Error(`Unknown group in family table for scenario ${id}: ${group}`);
    }
    if (groupToFamily.get(group) !== family) {
      throw new Error(`Mismatched group-to-family mapping for scenario ${id}: group '${group}' belongs to family '${groupToFamily.get(group)}', not '${family}'`);
    }
  }

  if (!table.aliases || typeof table.aliases !== 'object') {
    throw new Error('Family table missing aliases definition');
  }
  for (const [aliasName, aliasIds] of Object.entries(table.aliases)) {
    if (!Array.isArray(aliasIds)) {
      throw new Error(`Alias ${aliasName} in family table must be an array of scenario IDs`);
    }
    const aliasSeen = new Set();
    for (const scId of aliasIds) {
      if (!seenIds.has(scId)) {
        throw new Error(`Alias ${aliasName} references unknown scenario ID: ${scId}`);
      }
      if (aliasSeen.has(scId)) {
        throw new Error(`Duplicate scenario ID in alias ${aliasName}: ${scId}`);
      }
      aliasSeen.add(scId);
    }
  }

  return table;
}

export function validateFamilyTableAndRegister(table, register) {
  validateFamilyTable(table);
  if (!register || typeof register !== 'object' || !Array.isArray(register.scenarios)) {
    throw new Error('Invalid scenarios register');
  }

  const tableEntries = new Map(table.entries.map((e) => [e.id, e]));
  const registerScenarios = new Map();
  for (const s of register.scenarios) {
    if (!s || !s.id) {
      throw new Error('Invalid scenario record in register');
    }
    if (registerScenarios.has(s.id)) {
      throw new Error(`Duplicate scenario ID in register: ${s.id}`);
    }
    registerScenarios.set(s.id, s);
  }

  if (tableEntries.size !== registerScenarios.size) {
    throw new Error(`Family table and scenarios register disagree on scenario IDs: table has ${tableEntries.size}, register has ${registerScenarios.size}`);
  }

  for (const [id, entry] of tableEntries) {
    const regSc = registerScenarios.get(id);
    if (!regSc) {
      throw new Error(`Family table scenario ${id} missing from scenarios register`);
    }
    if (entry.group !== regSc.group) {
      throw new Error(`Family table and scenarios register disagree on group for ${id}: table=${entry.group}, register=${regSc.group}`);
    }
  }
  for (const id of registerScenarios.keys()) {
    if (!tableEntries.has(id)) {
      throw new Error(`Family table and scenarios register disagree on scenario IDs: scenario ${id} in register missing from table`);
    }
  }
}

export function resolveScenarioAuthority(table, targetScenarioIds) {
  if (!targetScenarioIds || targetScenarioIds.length === 0) {
    throw new Error('Target scenarios must not be empty');
  }
  const seen = new Set();
  const selectedFamilies = new Set();
  const entryMap = new Map((table.entries || []).map((e) => [e.id, e]));

  for (const id of targetScenarioIds) {
    if (seen.has(id)) {
      throw new Error(`Duplicate scenario ID in selection: ${id}`);
    }
    seen.add(id);

    const entry = entryMap.get(id);
    if (!entry) {
      throw new Error(`Unknown scenario ID in selection: ${id}`);
    }
    selectedFamilies.add(entry.family);
  }

  const familiesList = Array.isArray(table.families) ? table.families : Object.values(table.families || {});
  const familyMap = new Map();
  for (const f of familiesList) {
    const fId = f.id || f.family || f.name;
    if (fId) familyMap.set(fId, f);
  }

  if (selectedFamilies.size === 1) {
    const fam = Array.from(selectedFamilies)[0];
    const famObj = familyMap.get(fam);
    if (!famObj || !famObj.authority) {
      throw new Error(`Unknown family or missing authority for: ${fam}`);
    }
    return famObj.authority;
  }

  const supportedMixes = Array.isArray(table.supported_mixes) ? table.supported_mixes : [];
  for (const mix of supportedMixes) {
    const mixFams = new Set(mix.families || []);
    if (mixFams.size === selectedFamilies.size && Array.from(selectedFamilies).every((f) => mixFams.has(f))) {
      if (!mix.authority) {
        throw new Error(`Missing authority for supported mix: ${Array.from(mixFams).sort().join(', ')}`);
      }
      return mix.authority;
    }
  }

  throw new Error(`Unsupported scenario family mix: ${Array.from(selectedFamilies).sort().join(', ')}`);
}

export function writeReceiptFile(receiptPath, scenarios, browserVersions, startTime, artifactsDir, allArtifacts, manifestOrRegister = null, browserEnvironments = null, resolvedAuthority = null, customTablePath = null, customRegisterPath = null) {
  const passedCount = scenarios.filter((s) => s.status === 'passed').length;
  const failedCount = scenarios.filter((s) => s.status === 'failed').length;
  const artifactsList = Array.from(allArtifacts || []).sort();

  if (failedCount === 0 && artifactsDir) {
    for (const art of artifactsList) {
      const p = path.join(artifactsDir, art);
      if (!fs.existsSync(p) || fs.statSync(p).size === 0) {
        throw new Error(`Artifact ${art} missing or empty on disk at ${p}`);
      }
    }
  }

  let runnerHash = null;
  try {
    const runnerPath = path.resolve(__dirname, 'runner.mjs');
    if (fs.existsSync(runnerPath)) {
      runnerHash = crypto.createHash('sha256').update(fs.readFileSync(runnerPath)).digest('hex');
    }
  } catch {
    runnerHash = null;
  }

  let registerHash = null;
  try {
    const regP = customRegisterPath ? path.resolve(customRegisterPath) : path.resolve(__dirname, 'scenarios.json');
    if (fs.existsSync(regP)) {
      registerHash = crypto.createHash('sha256').update(fs.readFileSync(regP)).digest('hex');
    }
  } catch {
    registerHash = null;
  }

  const tblP = customTablePath ? path.resolve(customTablePath) : path.resolve(__dirname, 'family_table.json');
  const tableBytes = fs.readFileSync(tblP);
  const tableHash = crypto.createHash('sha256').update(tableBytes).digest('hex');
  const activeTable = JSON.parse(tableBytes.toString('utf-8'));
  validateFamilyTable(activeTable);

  const scenarioIds = Array.from(new Set(scenarios.map((s) => s.scenario_id || s.id).filter(Boolean)));
  if (scenarioIds.length === 0) {
    throw new Error('Target scenarios must not be empty');
  }
  const authority = resolveScenarioAuthority(activeTable, scenarioIds);
  if (resolvedAuthority && resolvedAuthority !== authority) {
    throw new Error('Resolved authority disagrees with receipt family table');
  }

  const manifest = manifestOrRegister || scenariosManifest;

  const receipt = {
    schema_version: '1.0.0',
    authority,
    disclaimer: manifest ? manifest.disclaimer : undefined,
    package: {
      name: '@playwright/test',
      version: '1.62.1',
    },
    runtime: {
      node_version: process.version,
      platform: process.platform,
      arch: process.arch,
      runner_sha256: runnerHash,
      register_sha256: registerHash,
      table_sha256: tableHash,
    },
    manifests: {
      runner_sha256: runnerHash,
      register_sha256: registerHash,
      table_sha256: tableHash,
    },
    table: {
      schema_version: activeTable ? activeTable.schema_version : '1.0.0',
      sha256: tableHash,
    },
    register: {
      schema_version: manifest ? manifest.schema_version : '1.0.0',
      sha256: registerHash,
    },
    browsers: browserVersions || {},
    browser_environments: browserEnvironments || {},
    timestamp: new Date().toISOString(),
    total_duration_ms: Date.now() - startTime,
    summary: {
      total: scenarios.length,
      passed: passedCount,
      failed: failedCount,
      skipped: 0,
    },
    scenarios,
    artifacts: artifactsList,
  };

  fs.writeFileSync(receiptPath, JSON.stringify(receipt, null, 2), 'utf-8');
  return receipt;
}

// Explicit allowed fixture files served by primary loopback server (Server 1)
const ALLOWED_FILES = new Map([
  ['/', 'index.html'],
  ['/index.html', 'index.html'],
  ['/frame.html', 'frame.html'],
  ['/popup.html', 'popup.html'],
  ['/sprite.svg', 'sprite.svg'],
  ['/worker.js', 'worker.js'],
  ['/module.js', 'module.js'],
  ['/submodule.js', 'submodule.js'],
]);

const ALLOWED_PATHS = new Set([
  '/',
  '/index.html',
  '/frame.html',
  '/popup.html',
  '/sprite.svg',
  '/worker.js',
  '/module.js',
  '/submodule.js',
  '/refused-module.js',
]);

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.svg': 'image/svg+xml; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
};

// Secondary server allowed endpoints (Server 2: cross-origin on different port)
const SERVER2_ALLOWED_PATHS = new Set([
  '/cors-allow',
  '/cors-deny',
  '/cors-preflight-allow',
  '/cors-preflight-deny',
  '/credentials',
  '/redirect',
  '/redirect-target',
]);

export function extractObservedRequest(req, expectedOrigin) {
  const parsedUrl = new URL(req.url, 'http://127.0.0.1');
  const pathname = parsedUrl.pathname.slice(0, 200);
  const method = req.method;
  const origin = req.headers.origin;
  const originMatch = Boolean(origin && origin === expectedOrigin);
  const preflightMethod = req.headers['access-control-request-method'] || null;
  const headerNames = Object.keys(req.headers).sort();
  const preflightHeaders = req.headers['access-control-request-headers']
    ? req.headers['access-control-request-headers'].split(',').map((h) => h.trim().toLowerCase()).sort()
    : [];
  const rawCookie = req.headers.cookie || '';
  const hasSyntheticCookie = Boolean(rawCookie && rawCookie.includes('apg_auth_cred=synthetic_token_125'));

  return {
    path: pathname,
    method,
    originMatch,
    preflightMethod,
    preflightHeaders,
    headerNames,
    hasSyntheticCookie,
    timestamp: Date.now(),
  };
}

// Start primary ephemeral loopback server
export function startServer() {
  return new Promise((resolve, reject) => {
    const observedRequests = [];
    const server = http.createServer((req, res) => {
      try {
        const parsedUrl = new URL(req.url, 'http://127.0.0.1');
        const rawPath = parsedUrl.pathname;

        // Record bounded request observation without raw headers/cookies
        observedRequests.push(extractObservedRequest(req, null));

        // Block path traversal or escaping
        if (req.url.includes('..') || req.url.includes('%2e') || req.url.includes('%2E')) {
          res.statusCode = 403;
          res.setHeader('Content-Type', 'text/plain');
          res.end('Forbidden');
          return;
        }

        // Serve only explicit owned HTML/SVG/JS files
        if (!ALLOWED_FILES.has(rawPath)) {
          res.statusCode = 404;
          res.setHeader('Content-Type', 'text/plain');
          res.end('Not Found');
          return;
        }

        const fileName = ALLOWED_FILES.get(rawPath);
        const safeFilePath = path.resolve(__dirname, fileName);

        // Verify resolved path is direct regular file inside fixtures
        const stat = fs.lstatSync(safeFilePath);
        if (stat.isSymbolicLink() || !stat.isFile() || !safeFilePath.startsWith(__dirname)) {
          res.statusCode = 403;
          res.setHeader('Content-Type', 'text/plain');
          res.end('Forbidden');
          return;
        }

        const ext = path.extname(safeFilePath).toLowerCase();
        const contentType = MIME_TYPES[ext] || 'application/octet-stream';
        res.statusCode = 200;
        res.setHeader('Content-Type', contentType);
        res.end(fs.readFileSync(safeFilePath));
      } catch (err) {
        res.statusCode = 500;
        res.end('Internal Error');
      }
    });

    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port;
      resolve({
        server,
        port,
        origin: `http://127.0.0.1:${port}`,
        getObservedRequests: () => [...observedRequests],
      });
    });
    server.on('error', reject);
  });
}

// Start secondary ephemeral loopback server for CORS, preflight, credentials, and redirects
export function startSecondaryServer(primaryOrigin) {
  return new Promise((resolve, reject) => {
    const observedRequests = [];

    const server = http.createServer((req, res) => {
      try {
        const parsedUrl = new URL(req.url, 'http://127.0.0.1');
        const pathname = parsedUrl.pathname;

        // Record bounded request observation without raw headers/cookies
        observedRequests.push(extractObservedRequest(req, primaryOrigin));

        // Block path traversal or escaping
        if (req.url.includes('..') || req.url.includes('%2e') || req.url.includes('%2E')) {
          res.statusCode = 403;
          res.setHeader('Content-Type', 'text/plain');
          res.end('Forbidden');
          return;
        }

        if (pathname === '/cors-allow') {
          res.statusCode = 200;
          res.setHeader('Content-Type', 'application/json');
          res.setHeader('Access-Control-Allow-Origin', req.headers.origin || primaryOrigin);
          res.end(JSON.stringify({ allowed: true, message: 'CORS allowed successfully' }));
          return;
        }

        if (pathname === '/cors-deny') {
          // Intentionally omitting Access-Control-Allow-Origin header to trigger CORS failure
          res.statusCode = 200;
          res.setHeader('Content-Type', 'application/json');
          res.end(JSON.stringify({ allowed: false, message: 'No CORS headers present' }));
          return;
        }

        if (pathname === '/cors-preflight-allow') {
          if (req.method === 'OPTIONS') {
            res.statusCode = 204;
            res.setHeader('Access-Control-Allow-Origin', req.headers.origin || primaryOrigin);
            res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, OPTIONS');
            res.setHeader('Access-Control-Allow-Headers', 'X-Custom-Header, Content-Type');
            res.setHeader('Access-Control-Max-Age', '86400');
            res.end();
            return;
          }
          if (req.method === 'PUT') {
            res.statusCode = 200;
            res.setHeader('Content-Type', 'application/json');
            res.setHeader('Access-Control-Allow-Origin', req.headers.origin || primaryOrigin);
            res.end(JSON.stringify({ preflightSuccess: true, method: req.method }));
            return;
          }
          res.statusCode = 405;
          res.end();
          return;
        }

        if (pathname === '/cors-preflight-deny') {
          if (req.method === 'OPTIONS') {
            res.statusCode = 403;
            res.end('Preflight Denied');
            return;
          }
          res.statusCode = 403;
          res.end();
          return;
        }

        if (pathname === '/credentials') {
          res.statusCode = 200;
          res.setHeader('Content-Type', 'application/json');
          res.setHeader('Access-Control-Allow-Origin', req.headers.origin || primaryOrigin);
          res.setHeader('Access-Control-Allow-Credentials', 'true');
          const hasSyntheticCookie = Boolean(req.headers.cookie && req.headers.cookie.includes('apg_auth_cred=synthetic_token_125'));
          res.end(JSON.stringify({
            credentialsObserved: true,
            hasSyntheticCookie,
          }));
          return;
        }

        if (pathname === '/redirect') {
          res.statusCode = 302;
          res.setHeader('Location', '/redirect-target');
          res.setHeader('Access-Control-Allow-Origin', req.headers.origin || primaryOrigin);
          res.end();
          return;
        }

        if (pathname === '/redirect-target') {
          res.statusCode = 200;
          res.setHeader('Content-Type', 'application/json');
          res.setHeader('Access-Control-Allow-Origin', req.headers.origin || primaryOrigin);
          res.end(JSON.stringify({ redirected: true, message: 'Target reached successfully' }));
          return;
        }

        res.statusCode = 404;
        res.setHeader('Content-Type', 'text/plain');
        res.end('Not Found');
      } catch (err) {
        res.statusCode = 500;
        res.end('Internal Error');
      }
    });

    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port;
      const origin = `http://127.0.0.1:${port}`;
      resolve({
        server,
        port,
        origin,
        getObservedRequests: () => [...observedRequests],
      });
    });
    server.on('error', reject);
  });
}

// Secure context creation with mandatory serviceWorkers block and route allowlist before any page
async function createSecureContext(browser, serverOrigin, secondaryOrigin = null, customRouteHandler = null) {
  if (typeof secondaryOrigin === 'function') {
    customRouteHandler = secondaryOrigin;
    secondaryOrigin = null;
  }
  const context = await browser.newContext({ serviceWorkers: 'block' });
  await context.route('**/*', (route) => {
    if (customRouteHandler) {
      return customRouteHandler(route);
    }
    let parsedUrl;
    try {
      parsedUrl = new URL(route.request().url());
    } catch {
      return route.abort('blockedbyclient');
    }
    if (parsedUrl.protocol === 'blob:') {
      if (parsedUrl.origin === serverOrigin || parsedUrl.origin === secondaryOrigin) {
        return route.continue();
      }
      return route.abort('blockedbyclient');
    }
    if (parsedUrl.protocol === 'data:' || parsedUrl.protocol === 'about:') {
      return route.continue();
    }
    if (parsedUrl.origin === serverOrigin) {
      if (ALLOWED_PATHS.has(parsedUrl.pathname)) {
        return route.continue();
      }
      return route.abort('blockedbyclient');
    }
    if (secondaryOrigin && parsedUrl.origin === secondaryOrigin) {
      if (SERVER2_ALLOWED_PATHS.has(parsedUrl.pathname)) {
        return route.continue();
      }
      return route.abort('blockedbyclient');
    }
    return route.abort('blockedbyclient');
  });
  return context;
}


async function executeScenario(scenarioId, browserName, page, context, serverOrigin, secondaryOrigin, platform, serverObservers = {}) {
  const { getServer1Requests = () => [], getServer2Requests = () => [] } = serverObservers;
  const assertions = [];
  const artifacts = [];

  switch (scenarioId) {
    case 'PW01': {
      await page.goto(`${serverOrigin}/index.html`);
      await page.locator('#single-btn').click();
      assertions.push({ name: 'unique_locator_success', passed: true });

      const ambiguous = page.locator('.dup-btn');
      await expect(ambiguous).toHaveCount(2);
      let strictViolationCaught = false;
      try {
        // This checks semantic strictness, not a subsecond scheduling deadline.
        await ambiguous.click({ timeout: 5000 });
      } catch (err) {
        if (err.message.includes('strict mode violation') && err.message.includes('resolved to 2 elements')) {
          strictViolationCaught = true;
        } else {
          throw err;
        }
      }
      if (!strictViolationCaught) throw new Error('Expected strict mode violation for locator(".dup-btn")');
      assertions.push({ name: 'strict_mode_violation_rejection', passed: true });
      break;
    }

    case 'PW02': {
      await page.goto(`${serverOrigin}/index.html`);
      await page.locator('#delayed-btn').click({ timeout: 2000 });
      assertions.push({ name: 'auto_wait_enablement_success', passed: true });

      let disabledTimeout = false;
      try {
        await page.locator('#permanent-disabled').click({ timeout: 150 });
      } catch (err) {
        if (err.message.includes('Timeout 150ms exceeded') && err.message.includes('disabled')) {
          disabledTimeout = true;
        }
      }
      if (!disabledTimeout) throw new Error('Expected timeout on permanently disabled button');
      assertions.push({ name: 'disabled_timeout_rejection', passed: true });
      break;
    }

    case 'PW03': {
      await page.goto(`${serverOrigin}/index.html`);
      await expect(page.locator('#status-box')).toHaveText('Ready State', { timeout: 2000 });
      assertions.push({ name: 'retrying_assertion_success', passed: true });

      let assertionRejected = false;
      try {
        await expect(page.locator('#status-box')).toHaveText('Impossible Value', { timeout: 150 });
      } catch (err) {
        if (err.message.includes('expect(locator).toHaveText(expected)') && err.message.includes('Impossible Value')) {
          assertionRejected = true;
        }
      }
      if (!assertionRejected) throw new Error('Expected narrow failure for impossible webfirst assertion');
      assertions.push({ name: 'retrying_assertion_rejection', passed: true });
      break;
    }

    case 'PW04': {
      const testUrl = `${serverOrigin}/index.html`;
      const contextA = await createSecureContext(page.context().browser(), serverOrigin);
      const contextB = await createSecureContext(page.context().browser(), serverOrigin);
      const pageA = await contextA.newPage();
      const pageB = await contextB.newPage();

      try {
        await pageA.goto(testUrl);
        await contextA.addCookies([{ name: 'session_auth', value: 'secret_123', url: testUrl }]);
        await pageA.evaluate(() => localStorage.setItem('user_pref', 'theme_dark'));

        const cookiesA = await contextA.cookies(testUrl);
        const prefA = await pageA.evaluate(() => localStorage.getItem('user_pref'));
        if (cookiesA.length === 0 || prefA !== 'theme_dark') {
          throw new Error('Failed to set state in context A');
        }
        assertions.push({ name: 'context_a_state_populated', passed: true });

        await pageB.goto(testUrl);
        const cookiesB = await contextB.cookies(testUrl);
        const prefB = await pageB.evaluate(() => localStorage.getItem('user_pref'));
        if (cookiesB.length !== 0 || prefB !== null) {
          throw new Error('State leaked into context B');
        }
        assertions.push({ name: 'context_b_state_clean', passed: true });
      } finally {
        await contextA.close();
        await contextB.close();
      }
      break;
    }

    case 'PW05': {
      await page.goto(`${serverOrigin}/index.html`);
      // 1. Explicit timeout
      let timeoutCaught = false;
      try {
        await page.locator('#nonexistent-element').click({ timeout: 150 });
      } catch (err) {
        if (err.message.includes('Timeout 150ms exceeded')) {
          timeoutCaught = true;
        }
      }
      if (!timeoutCaught) throw new Error('Expected timeout failure');
      assertions.push({ name: 'explicit_timeout_rejection', passed: true });

      // 2. Playwright 1.62 AbortController.signal locator click cancellation
      const controller = new AbortController();
      setTimeout(() => controller.abort('Test Operation Cancelled'), 60);

      let signalAbortCaught = false;
      try {
        await page.locator('#permanent-disabled').click({ signal: controller.signal, timeout: 5000 });
      } catch (err) {
        if (err.name === 'AbortError' || err.message.includes('Test Operation Cancelled') || err.message.includes('operation was aborted')) {
          signalAbortCaught = true;
        }
      }
      if (!signalAbortCaught) throw new Error('Expected AbortController.signal locator click cancellation');
      assertions.push({ name: 'locator_click_signal_cancellation', passed: true });
      break;
    }

    case 'PW06': {
      let untrustedAborted = false;
      const routeContext = await createSecureContext(page.context().browser(), serverOrigin, (route) => {
        let reqUrl;
        try {
          reqUrl = new URL(route.request().url());
        } catch {
          untrustedAborted = true;
          return route.abort('blockedbyclient');
        }
        if (reqUrl.origin === serverOrigin && ALLOWED_PATHS.has(reqUrl.pathname)) {
          route.continue();
        } else {
          untrustedAborted = true;
          route.abort('blockedbyclient');
        }
      });
      const routePage = await routeContext.newPage();

      try {
        const resp = await routePage.goto(`${serverOrigin}/index.html`);
        if (resp.status() !== 200) throw new Error('Loopback route failed');
        assertions.push({ name: 'loopback_route_permitted', passed: true });

        let fetchFailed = false;
        try {
          await routePage.evaluate(async () => {
            await fetch('http://disallowed-network.invalid/leak');
          });
        } catch {
          fetchFailed = true;
        }
        if (!fetchFailed || !untrustedAborted) {
          throw new Error('Untrusted external network request was not aborted');
        }
        assertions.push({ name: 'untrusted_network_aborted', passed: true });
      } finally {
        await routeContext.close();
      }
      break;
    }

    case 'PW07': {
      await page.goto(`${serverOrigin}/index.html`);
      assertions.push({ name: 'page_navigation_complete', passed: true });

      const subframeText = await page.frameLocator('#child-frame').locator('h2').textContent();
      if (subframeText !== 'Frame Content') throw new Error('Subframe text mismatch');
      assertions.push({ name: 'subframe_locator_content', passed: true });

      const [popup] = await Promise.all([
        page.context().waitForEvent('page'),
        page.locator('#popup-trigger').click(),
      ]);
      await popup.waitForLoadState('domcontentloaded');
      const popupTitle = await popup.title();
      if (popupTitle !== 'Popup Window') throw new Error('Popup title mismatch');
      await popup.close();
      assertions.push({ name: 'popup_window_lifecycle', passed: true });
      break;
    }

    case 'PW08': {
      const traceRelName = `PW08-${browserName}-trace.zip`;
      const screenRelName = `PW08-${browserName}-screenshot.png`;
      const tracePath = path.join(artifactsDir, traceRelName);
      const screenPath = path.join(artifactsDir, screenRelName);

      const traceContext = await createSecureContext(page.context().browser(), serverOrigin);
      const tracePage = await traceContext.newPage();
      try {
        await traceContext.tracing.start({ screenshots: true, snapshots: true });
        await tracePage.goto(`${serverOrigin}/index.html`);
        await tracePage.screenshot({ path: screenPath });
        await traceContext.tracing.stop({ path: tracePath });

        if (!fs.existsSync(screenPath) || fs.statSync(screenPath).size === 0) {
          throw new Error('Screenshot artifact missing or empty');
        }
        artifacts.push(screenRelName);
        assertions.push({ name: 'screenshot_artifact_retained', passed: true });

        if (!fs.existsSync(tracePath) || fs.statSync(tracePath).size === 0) {
          throw new Error('Trace zip artifact missing or empty');
        }
        artifacts.push(traceRelName);
        assertions.push({ name: 'trace_zip_artifact_retained', passed: true });
      } finally {
        await traceContext.close();
      }
      break;
    }

    case 'PW09': {
      await page.goto(`${serverOrigin}/index.html`);
      const baseRel = `PW09-${browserName}-${platform}-baseline.png`;
      const reRel = `PW09-${browserName}-${platform}-re-render.png`;
      const negRel = `PW09-${browserName}-${platform}-negative.png`;
      const basePath = path.join(artifactsDir, baseRel);
      const rePath = path.join(artifactsDir, reRel);
      const negPath = path.join(artifactsDir, negRel);

      const target = page.locator('#visual-box');
      const bufBaseline = await target.screenshot({ path: basePath });
      artifacts.push(baseRel);

      const bufReRender = await target.screenshot({ path: rePath });
      artifacts.push(reRel);

      if (!bufBaseline.equals(bufReRender)) {
        throw new Error('Same-run baseline screenshot mismatch');
      }
      assertions.push({ name: 'same_run_render_identical', passed: true });

      await page.evaluate(() => {
        const el = document.getElementById('visual-box');
        el.style.background = '#e11d48';
        el.style.borderColor = '#881337';
      });
      const bufNegative = await target.screenshot({ path: negPath });
      artifacts.push(negRel);

      if (bufBaseline.equals(bufNegative)) {
        throw new Error('Controlled visual negative failed to produce screenshot difference');
      }
      assertions.push({ name: 'controlled_visual_negative_differs', passed: true });
      break;
    }

    case 'PW10': {
      const supervisorAssertions = await runPlaywrightSupervisor(browserName, scratchDir, serverOrigin);
      assertions.push(...supervisorAssertions);
      break;
    }

    case 'AX01': {
      await page.goto(`${serverOrigin}/index.html`);
      await expect(page.locator('#ax01-btn')).toHaveAccessibleName('Submit Order');
      assertions.push({ name: 'button_accessible_name', passed: true });

      await expect(page.locator('#ax01-link')).toHaveAccessibleName('User Profile Documentation');
      assertions.push({ name: 'link_aria_label', passed: true });

      await expect(page.locator('#ax01-input')).toHaveAccessibleName('Billing Address');
      assertions.push({ name: 'input_label_association', passed: true });
      break;
    }

    case 'AX02': {
      await page.goto(`${serverOrigin}/index.html`);
      await expect(page.locator('#ax02-empty-btn')).toHaveAccessibleName('');
      assertions.push({ name: 'empty_name_verified', passed: true });

      let rejected = false;
      try {
        await expect(page.locator('#ax02-empty-btn')).toHaveAccessibleName('Save Order', { timeout: 150 });
      } catch (err) {
        if (err.message.includes('expect(locator).toHaveAccessibleName(expected)') && err.message.includes('Save Order')) {
          rejected = true;
        }
      }
      if (!rejected) throw new Error('Expected narrow rejection for mismatched accessible name');
      assertions.push({ name: 'mismatched_name_narrow_rejection', passed: true });
      break;
    }

    case 'AX03': {
      await page.goto(`${serverOrigin}/index.html`);
      const section = page.locator('#section-ax03');
      await expect(section.getByRole('heading', { level: 1 })).toHaveText('Site Portal');
      await expect(section.getByRole('heading', { level: 2 })).toHaveText('Dashboard Overview');
      await expect(section.getByRole('heading', { level: 3 })).toHaveText('Quarterly Analytics');
      assertions.push({ name: 'heading_levels_resolved', passed: true });

      await expect(section.getByRole('banner')).toBeVisible();
      await expect(section.getByRole('navigation', { name: 'Primary Navigation' })).toBeVisible();
      await expect(section.getByRole('main')).toBeVisible();
      assertions.push({ name: 'landmarks_resolved', passed: true });
      break;
    }

    case 'AX04': {
      await page.goto(`${serverOrigin}/index.html`);
      const blurRel = `AX04-${browserName}-${platform}-blur.png`;
      const focusRel = `AX04-${browserName}-${platform}-focus.png`;
      const blurPath = path.join(artifactsDir, blurRel);
      const focusPath = path.join(artifactsDir, focusRel);

      await page.locator('#ax04-first').focus();
      const targetBtn = page.locator('#ax04-focus-target');
      // Include space outside the button border so its outline is not clipped.
      const focusRegion = page.locator('#section-ax04');
      const bufBlur = await focusRegion.screenshot({ path: blurPath });
      artifacts.push(blurRel);

      await page.keyboard.press('Tab');
      await expect(targetBtn).toBeFocused();
      const bufFocus = await focusRegion.screenshot({ path: focusPath });
      artifacts.push(focusRel);

      if (bufBlur.equals(bufFocus)) {
        throw new Error('Visible focus failed to produce rendered screenshot difference');
      }
      assertions.push({ name: 'focus_screenshot_differs_from_blur', passed: true });

      await page.keyboard.press('Tab');
      await expect(page.locator('#ax04-third')).toBeFocused();
      assertions.push({ name: 'tab_navigation_advances', passed: true });
      break;
    }

    case 'AX05': {
      await page.goto(`${serverOrigin}/index.html`);
      const svgBtn = page.locator('#ax05-svg');
      const out = page.locator('#ax05-output');

      await expect(svgBtn).toHaveAccessibleName('Toggle dark mode');
      assertions.push({ name: 'svg_accessible_name', passed: true });

      await page.locator('#ax04-third').focus();
      await page.keyboard.press('Tab');
      await expect(svgBtn).toBeFocused();
      assertions.push({ name: 'svg_keyboard_focus', passed: true });

      await page.keyboard.press('Enter');
      await expect(out).toHaveText('on');

      await page.keyboard.press('Space');
      await expect(out).toHaveText('off');
      assertions.push({ name: 'svg_enter_space_activation', passed: true });
      break;
    }

    case 'AX06': {
      await page.goto(`${serverOrigin}/index.html`);
      await expect(page.locator('#ax06-meaningful')).toHaveAccessibleName('System status operational');
      await expect(page.getByRole('img', { name: 'System status operational' })).toBeVisible();
      assertions.push({ name: 'meaningful_svg_role_and_name', passed: true });

      await expect(page.locator('#ax06-decorative')).toHaveAttribute('aria-hidden', 'true');
      await expect(page.locator('#ax06-decorative')).toHaveAccessibleName('');
      await page.locator('#ax06-decorative').focus();
      await expect(page.locator('#ax06-decorative')).not.toBeFocused();
      assertions.push({ name: 'decorative_svg_hidden_and_empty', passed: true });
      break;
    }

    case 'AX07': {
      await page.goto(`${serverOrigin}/index.html`);
      const section = page.locator('#section-ax07');
      await expect(section.getByRole('group', { name: 'Quarterly Regional Distribution' })).toBeVisible();
      assertions.push({ name: 'figure_group_labelled', passed: true });

      await expect(section.getByRole('img', { name: 'Quarterly distribution chart' })).toBeVisible();
      assertions.push({ name: 'svg_image_labelled', passed: true });

      await expect(section.getByRole('table', { name: 'Quarterly Regional Distribution data alternative' })).toBeVisible();
      await expect(section.getByRole('columnheader', { name: 'Region' })).toBeVisible();
      await expect(section.getByRole('columnheader', { name: 'Percentage' })).toBeVisible();
      await expect(section.getByRole('row')).toHaveText(['RegionPercentage', 'Region Alpha60%', 'Region Beta40%']);
      await expect(section.locator('svg text')).toHaveText(['Region Alpha 60%', 'Region Beta 40%']);
      assertions.push({ name: 'table_data_headers_accessible', passed: true });
      await section.getByRole('table').evaluate(table => table.remove());
      await expect(section.getByRole('table')).toHaveCount(0);
      await expect(section.getByRole('img')).toHaveAccessibleName('Quarterly distribution chart');
      assertions.push({ name: 'short_name_does_not_supply_missing_data_alternative', passed: true });
      break;
    }

    case 'AX08': {
      await page.goto(`${serverOrigin}/index.html`);
      await expect(page.locator('#ax08-hidden')).toBeHidden();
      await expect(page.getByRole('button', { name: 'Hidden Button', exact: true })).toHaveCount(0);
      await page.locator('#ax08-hidden').focus();
      await expect(page.locator('#ax08-hidden')).not.toBeFocused();
      assertions.push({ name: 'element_hidden_verified', passed: true });

      await expect(page.locator('#ax08-disabled')).toBeDisabled();
      await expect(page.getByRole('button', { name: 'Disabled Button', exact: true })).toHaveCount(1);
      await page.locator('#ax08-disabled').focus();
      await expect(page.locator('#ax08-disabled')).not.toBeFocused();
      assertions.push({ name: 'element_disabled_verified', passed: true });

      let inertRejected = false;
      try {
        await page.locator('#ax08-inert-btn').click({ timeout: 200 });
      } catch (err) {
        if (err.message.includes('not visible') || err.message.includes('Timeout') || err.message.includes('intercepts pointer')) {
          inertRejected = true;
        }
      }
      if (!inertRejected) throw new Error('Expected inert button interaction rejection');
      // In 1.62.1 role lookup observes this inert DOM button. It is not a
      // platform accessibility-tree query; interaction/focus prove another layer.
      await expect(page.getByRole('button', { name: 'Inert Button', exact: true })).toHaveCount(1);
      await page.locator('#ax08-inert-btn').focus();
      await expect(page.locator('#ax08-inert-btn')).not.toBeFocused();
      assertions.push({ name: 'inert_interaction_rejected', passed: true,
        limitation: 'Role locator includes inert DOM content; this is not platform accessibility-tree exposure evidence.' });
      break;
    }

    case 'AX09': {
      await page.goto(`${serverOrigin}/index.html`);
      const statusEl = page.locator('#ax09-status');
      await expect(statusEl).toHaveAttribute('role', 'status');
      await expect(statusEl).toHaveAttribute('aria-live', 'polite');
      assertions.push({ name: 'live_region_role_attributes', passed: true });

      await page.evaluate(() => window.setLiveStatus('Database migration completed'));
      await expect(statusEl).toHaveText('Database migration completed');
      if (!(await statusEl.ariaSnapshot()).includes('Database migration completed')) {
        throw new Error('Updated live-region text absent from semantic snapshot');
      }
      assertions.push({
        name: 'dynamic_message_text_updated',
        passed: true,
        disclaimer: 'Evidence confirms DOM mutation and accessibility role=status / aria-live=polite attribute presence; makes NO claim of screen reader speech synthesis or assistive technology audio presentation.',
      });
      break;
    }

    case 'AX10': {
      await page.goto(`${serverOrigin}/index.html`);
      const snapshot = await page.locator('#ax10-tree').ariaSnapshot();
      if (!snapshot.includes('navigation "Portal Nav"') ||
          !snapshot.includes('link "Feed"') ||
          !snapshot.includes('link "Settings"') ||
          !snapshot.includes('heading "User Profile" [level=1]') ||
          !snapshot.includes('button "Update Avatar"')) {
        throw new Error(`Unexpected ARIA snapshot:\n${snapshot}`);
      }
      assertions.push({ name: 'aria_snapshot_structure_matches', passed: true });
      break;
    }

    case 'AX11': {
      await page.goto(`${serverOrigin}/index.html`);
      const section = page.locator('#section-ax11');
      const isValidInitial = await page.evaluate(() => document.getElementById('ax11-required').checkValidity());
      if (isValidInitial !== false) throw new Error('Expected initial checkValidity to be false');
      await page.locator('#ax11-required').fill('Host Validated');
      const isValidFilled = await page.evaluate(() => document.getElementById('ax11-required').checkValidity());
      if (isValidFilled !== true) throw new Error('Expected filled checkValidity to be true');
      assertions.push({ name: 'form_constraint_validation', passed: true });

      await expect(section.getByRole('table', { name: 'Server Metrics' })).toBeVisible();
      await expect(section.getByRole('columnheader', { name: 'Host' })).toBeVisible();
      assertions.push({ name: 'table_headers_accessible', passed: true });

      await page.emulateMedia({ reducedMotion: 'reduce' });
      const reduceMatches = await page.evaluate(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches);
      if (!reduceMatches) throw new Error('Expected prefers-reduced-motion to be reduce');

      await page.emulateMedia({ reducedMotion: 'no-preference' });
      const noPrefMatches = await page.evaluate(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches);
      if (noPrefMatches) throw new Error('Expected prefers-reduced-motion to be no-preference');
      assertions.push({ name: 'reduced_motion_emulation', passed: true });
      break;
    }

    case 'SVG01': {
      // Observe browser's actual network response for sprite.svg during navigation
      let spriteReceived = false;
      const respPromise = page.waitForResponse(
        (resp) => resp.url().includes('sprite.svg') && resp.status() === 200,
        { timeout: 5000 }
      ).then(() => { spriteReceived = true; }).catch(() => {});

      await page.goto(`${serverOrigin}/index.html`);
      await respPromise;
      if (!spriteReceived) {
        throw new Error('Browser did not receive successful response for external sprite.svg');
      }
      assertions.push({ name: 'browser_requested_sprite_response', passed: true });

      // Compare SAME locator (#svg01-target) with equal dimensions: permitted vs missing symbol
      const targetLocator = page.locator('#svg01-target');
      const starBuf = await targetLocator.screenshot();

      // Change href to missing symbol on the SAME locator
      await page.evaluate(() => {
        document.getElementById('svg01-use').setAttribute('href', '/sprite.svg#missing-symbol');
      });
      const missingBuf = await targetLocator.screenshot();

      if (starBuf.equals(missingBuf)) {
        throw new Error('Rendered SVG symbol did not produce visible difference against missing symbol on same locator');
      }
      assertions.push({ name: 'same_locator_rendered_differs_from_missing', passed: true });
      break;
    }

    case 'SVG02': {
      let foreignOriginAborted = false;
      const svgRouteContext = await createSecureContext(page.context().browser(), serverOrigin, (route) => {
        let reqUrl;
        try {
          reqUrl = new URL(route.request().url());
        } catch {
          foreignOriginAborted = true;
          return route.abort('blockedbyclient');
        }
        if (reqUrl.origin === serverOrigin && ALLOWED_PATHS.has(reqUrl.pathname)) {
          route.continue();
        } else {
          foreignOriginAborted = true;
          route.abort('blockedbyclient');
        }
      });
      const svgRoutePage = await svgRouteContext.newPage();

      try {
        await svgRoutePage.goto(`${serverOrigin}/index.html`);
        const target = svgRoutePage.locator('#svg02-target');
        const blank = await target.screenshot();
        // Reference foreign origin in <use> tag. Engines may refuse this before
        // routing; visible absence and the separate routing probe are distinct.
        await svgRoutePage.evaluate(() => {
          document.getElementById('svg02-use').setAttribute('href', 'http://unauthorized-cdn.invalid/remote-sprite.svg#icon');
        });

        // Visible absence on #svg02-target
        const emptyBuf = await target.screenshot();
        if (!blank.equals(emptyBuf)) throw new Error('Forbidden SVG changed the empty target');
        await svgRoutePage.evaluate(() => document.getElementById('svg02-use').setAttribute('href', '/sprite.svg#star-symbol'));
        const permitted = await target.screenshot();
        if (blank.equals(permitted)) throw new Error('SVG negative control lacks a visible permitted counterpart');
        assertions.push({ name: 'foreign_svg_visible_absence_verified', passed: true });

        // Secondary JS fetch check to .invalid domain
        let fetchThrew = false;
        try {
          await svgRoutePage.evaluate(async () => {
            await fetch('http://unauthorized-cdn.invalid/remote-sprite.svg');
          });
        } catch {
          fetchThrew = true;
        }
        if (!fetchThrew || !foreignOriginAborted) {
          throw new Error('Cross-origin SVG resource was not aborted');
        }
        assertions.push({ name: 'foreign_svg_reference_aborted', passed: true,
          evidence: 'Foreign use remains empty under browser/resource policy; separate fetch proves route refusal, not that use reached routing.' });
      } finally {
        await svgRouteContext.close();
      }
      break;
    }

    case 'SVG03': {
      // 1. Attempt path traversal in SVG <use> href
      await page.goto(`${serverOrigin}/index.html`);
      const target = page.locator('#svg03-target');
      const blank = await target.screenshot();
      const blockedRequest = page.waitForEvent('requestfailed', {
        predicate: request => request.url() === `${serverOrigin}/etc/passwd`, timeout: 5000,
      });
      await page.evaluate(() => {
        document.getElementById('svg03-use').setAttribute('href', '/../etc/passwd#symbol');
      });
      await blockedRequest;

      // Target renders visibly absent (empty)
      const emptyBuf = await target.screenshot();
      if (!blank.equals(emptyBuf)) throw new Error('Forbidden SVG path changed empty target');
      await page.evaluate(() => document.getElementById('svg03-use').setAttribute('href', '/sprite.svg#star-symbol'));
      if (blank.equals(await target.screenshot())) throw new Error('SVG path negative lacks a visible permitted counterpart');
      assertions.push({ name: 'path_traversal_visible_absence_verified', passed: true });

      // 2. Direct HTTP path traversal returns 403 Forbidden
      const urlObj = new URL(serverOrigin);
      const traversalStatus = await new Promise((resolve, reject) => {
        const req = http.request({
          host: urlObj.hostname,
          port: urlObj.port,
          path: '/../etc/passwd',
          method: 'GET',
        }, (res) => {
          resolve(res.statusCode);
        });
        req.on('error', reject);
        req.end();
      });

      if (traversalStatus !== 403) {
        throw new Error(`Expected 403 Forbidden for path traversal, got ${traversalStatus}`);
      }
      assertions.push({ name: 'path_traversal_svg_reference_blocked', passed: true });
      break;
    }

    case 'BR01': {
      await page.goto(`${serverOrigin}/index.html`);
      const lifecycle = await page.evaluate(() => {
        return {
          states: window.__lifecycle ? window.__lifecycle.states : [],
          events: window.__lifecycle ? window.__lifecycle.events : [],
          identities: window.__lifecycle ? window.__lifecycle.identities : null,
          currentReadyState: document.readyState,
          visibilityState: document.visibilityState,
        };
      });

      // 1. Window/Document identity check
      if (!lifecycle.identities || !lifecycle.identities.windowDocMatch ||
          !lifecycle.identities.defaultViewMatch || !lifecycle.identities.selfMatch ||
          !lifecycle.identities.windowMatch) {
        throw new Error(`Window/Document identity mismatch: ${JSON.stringify(lifecycle.identities)}`);
      }

      // 2. readyState transitions: loading < interactive < complete
      const loadingIdx = lifecycle.states.indexOf('loading');
      const interactiveIdx = lifecycle.states.indexOf('interactive');
      const completeIdx = lifecycle.states.indexOf('complete');
      if (loadingIdx === -1 || interactiveIdx === -1 || completeIdx === -1) {
        throw new Error(`readyState transitions missing states: ${JSON.stringify(lifecycle.states)}`);
      }
      if (!(loadingIdx < interactiveIdx && interactiveIdx < completeIdx)) {
        throw new Error(`readyState transitions out of order (must be loading < interactive < complete): ${JSON.stringify(lifecycle.states)}`);
      }
      if (lifecycle.currentReadyState !== 'complete') {
        throw new Error(`Expected readyState complete, got ${lifecycle.currentReadyState}`);
      }
      assertions.push({ name: 'document_readystate_order_verified', passed: true });

      // 3. Lifecycle events deterministic order: DOMContentLoaded < load <= pageshow
      const events = lifecycle.events;
      const dclIndex = events.indexOf('DOMContentLoaded');
      const loadIndex = events.indexOf('load');
      const pageshowIndex = events.indexOf('pageshow');
      if (dclIndex === -1 || loadIndex === -1 || pageshowIndex === -1) {
        throw new Error(`Lifecycle events missing: ${JSON.stringify(events)}`);
      }
      if (!(dclIndex < loadIndex && loadIndex <= pageshowIndex)) {
        throw new Error(`Lifecycle events out of order: ${JSON.stringify(events)}`);
      }
      assertions.push({ name: 'lifecycle_events_deterministic_order', passed: true });

      const visibility = lifecycle.visibilityState;
      if (visibility !== 'visible') {
        throw new Error(`Expected visibilityState 'visible', got '${visibility}'`);
      }
      assertions.push({ name: 'visibility_state_active', passed: true });
      break;
    }

    case 'BR02': {
      await page.goto(`${serverOrigin}/index.html`);
      const result = await page.evaluate(async () => {
        const container = document.getElementById('br02-container');

        // 1. Parser script ran during HTML parsing
        const parserScriptRan = (window.__br02ParserScriptRan === true);

        // 2. innerHTML script is inert in HTML5 (must NOT execute)
        container.innerHTML = '<script>window.__br02InnerHtmlRan = true;<\\/script>';
        const innerHtmlScriptInert = (typeof window.__br02InnerHtmlRan === 'undefined');

        // 3. Dynamic script insertion via appendChild executes
        const dynamicScript = document.createElement('script');
        dynamicScript.textContent = 'window.__dynamicScriptRan = true;';
        container.appendChild(dynamicScript);
        const dynamicScriptRan = (window.__dynamicScriptRan === true);

        // 4. MutationObserver capturing exact childList and attributes records
        const observedRecords = [];
        const observer = new MutationObserver((mutations) => {
          for (const m of mutations) {
            observedRecords.push({
              type: m.type,
              targetId: m.target.id,
              attributeName: m.attributeName || null,
              addedNodesCount: m.addedNodes ? m.addedNodes.length : 0,
            });
          }
        });
        observer.observe(container, { childList: true, attributes: true, subtree: true });

        // Trigger exact childList mutation
        const child = document.createElement('span');
        child.id = 'br02-child';
        container.appendChild(child);

        // Trigger exact attribute mutation
        container.setAttribute('data-test', 'mutation-value');

        // Wait for microtask delivery
        await new Promise((resolve) => setTimeout(resolve, 30));
        const capturedCount = observedRecords.length;
        const recordsSnapshot = [...observedRecords];

        // 5. Disconnect observer cleanly
        observer.disconnect();

        // Subsequent mutations after disconnect must NOT be observed
        container.setAttribute('data-test', 'after-disconnect');
        container.appendChild(document.createElement('div'));
        await new Promise((resolve) => setTimeout(resolve, 30));
        const afterDisconnectCount = observedRecords.length;

        return {
          parserScriptRan,
          innerHtmlScriptInert,
          dynamicScriptRan,
          recordsSnapshot,
          capturedCount,
          afterDisconnectCount,
        };
      });

      if (!result.parserScriptRan) throw new Error('Parser-inserted script failed to execute');
      if (!result.innerHtmlScriptInert) throw new Error('innerHTML-inserted script was not inert (unexpected execution)');
      if (!result.dynamicScriptRan) throw new Error('Dynamically appended script failed to execute');
      assertions.push({ name: 'parser_and_dynamic_scripts_executed', passed: true });

      const childRecord = result.recordsSnapshot.find((r) => r.type === 'childList' && r.targetId === 'br02-container' && r.addedNodesCount === 1);
      const attrRecord = result.recordsSnapshot.find((r) => r.type === 'attributes' && r.targetId === 'br02-container' && r.attributeName === 'data-test');
      if (!childRecord || !attrRecord) {
        throw new Error(`Exact MutationObserver records not captured: ${JSON.stringify(result.recordsSnapshot)}`);
      }
      assertions.push({ name: 'mutation_observer_records_captured', passed: true });

      if (result.afterDisconnectCount !== result.capturedCount) {
        throw new Error('MutationObserver observed events after disconnect');
      }
      assertions.push({ name: 'mutation_observer_disconnected_cleanly', passed: true });
      break;
    }

    case 'BR03': {
      await page.goto(`${serverOrigin}/index.html`);
      const eventResult = await page.evaluate(() => {
        const parent = document.getElementById('br03-parent');
        const target = document.getElementById('br03-target');
        const checkboxPos = document.getElementById('br03-checkbox-positive');
        const checkboxCanc = document.getElementById('br03-checkbox-canceled');
        const phaseOrder = [];

        // 1. Capture -> Target -> Bubble phase order
        const parentCapture = () => phaseOrder.push('parent-capture');
        const targetListener = () => phaseOrder.push('target');
        const parentBubble = () => phaseOrder.push('parent-bubble');

        parent.addEventListener('click', parentCapture, { capture: true });
        target.addEventListener('click', targetListener);
        parent.addEventListener('click', parentBubble, { capture: false });

        target.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));

        parent.removeEventListener('click', parentCapture, { capture: true });
        target.removeEventListener('click', targetListener);
        parent.removeEventListener('click', parentBubble, { capture: false });

        // 2. Cancellation: stopPropagation in capture halts traversal
        const stopPropagationOrder = [];
        const stoppingCapture = (e) => {
          stopPropagationOrder.push('stopping-capture');
          e.stopPropagation();
        };
        const unreachableTarget = () => stopPropagationOrder.push('unreachable');
        parent.addEventListener('click', stoppingCapture, { capture: true });
        target.addEventListener('click', unreachableTarget);

        target.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
        parent.removeEventListener('click', stoppingCapture, { capture: true });
        target.removeEventListener('click', unreachableTarget);

        // 3. Checkbox default action positive vs canceled control
        checkboxPos.checked = false;
        checkboxPos.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
        const positiveDefaultActionRan = (checkboxPos.checked === true);

        checkboxCanc.checked = false;
        const cancelListener = (e) => {
          e.preventDefault();
        };
        checkboxCanc.addEventListener('click', cancelListener);
        const cancelEvent = new MouseEvent('click', { bubbles: true, cancelable: true });
        checkboxCanc.dispatchEvent(cancelEvent);
        const canceledDefaultActionHalted = (cancelEvent.defaultPrevented === true && checkboxCanc.checked === false);
        checkboxCanc.removeEventListener('click', cancelListener);

        // 4. Listener options: once, and removal
        let onceCount = 0;
        const onceListener = () => onceCount++;
        target.addEventListener('click', onceListener, { once: true });
        target.dispatchEvent(new MouseEvent('click'));
        target.dispatchEvent(new MouseEvent('click'));

        let removedCount = 0;
        const removeMe = () => removedCount++;
        target.addEventListener('click', removeMe);
        target.dispatchEvent(new MouseEvent('click'));
        target.removeEventListener('click', removeMe);
        target.dispatchEvent(new MouseEvent('click'));

        return {
          phaseOrder,
          stopPropagationOrder,
          positiveDefaultActionRan,
          canceledDefaultActionHalted,
          onceCount,
          removedCount,
        };
      });

      const expectedPhases = ['parent-capture', 'target', 'parent-bubble'];
      if (JSON.stringify(eventResult.phaseOrder) !== JSON.stringify(expectedPhases)) {
        throw new Error(`Event phase order mismatch: expected ${JSON.stringify(expectedPhases)}, got ${JSON.stringify(eventResult.phaseOrder)}`);
      }
      assertions.push({ name: 'event_phase_order_verified', passed: true });

      if (eventResult.stopPropagationOrder.length !== 1 || eventResult.stopPropagationOrder[0] !== 'stopping-capture') {
        throw new Error(`stopPropagation failed: ${JSON.stringify(eventResult.stopPropagationOrder)}`);
      }
      assertions.push({ name: 'event_propagation_cancellation', passed: true });

      if (!eventResult.positiveDefaultActionRan || !eventResult.canceledDefaultActionHalted) {
        throw new Error(`Checkbox default action control failed: positive=${eventResult.positiveDefaultActionRan}, canceled=${eventResult.canceledDefaultActionHalted}`);
      }
      assertions.push({ name: 'event_default_prevented', passed: true });

      if (eventResult.onceCount !== 1 || eventResult.removedCount !== 1) {
        throw new Error(`Listener options/removal failed: once=${eventResult.onceCount}, removed=${eventResult.removedCount}`);
      }
      assertions.push({ name: 'event_listener_options_and_removal', passed: true });
      break;
    }

    case 'BR04': {
      await page.goto(`${serverOrigin}/index.html`);
      const timingResult = await page.evaluate(async () => {
        const sequence = [];

        // 1. Microtask drains before next macrotask
        setTimeout(() => sequence.push('macrotask-1'), 0);
        queueMicrotask(() => sequence.push('microtask-1'));
        Promise.resolve().then(() => sequence.push('microtask-2'));

        await new Promise((resolve) => setTimeout(resolve, 50));

        // 2. rAF executes
        let rafTimestamp = 0;
        await new Promise((resolve) => {
          requestAnimationFrame((ts) => {
            rafTimestamp = ts;
            resolve();
          });
        });

        // 3. Timer and rAF cancellation cleanup
        let timeoutFired = false;
        let rafFired = false;
        const tId = setTimeout(() => { timeoutFired = true; }, 30);
        clearTimeout(tId);

        const rId = requestAnimationFrame(() => { rafFired = true; });
        cancelAnimationFrame(rId);

        await new Promise((resolve) => setTimeout(resolve, 60));

        return {
          sequence,
          rafTimestamp,
          timeoutFired,
          rafFired,
        };
      });

      const m1 = timingResult.sequence.indexOf('microtask-1');
      const m2 = timingResult.sequence.indexOf('microtask-2');
      const macro = timingResult.sequence.indexOf('macrotask-1');
      if (m1 === -1 || m2 === -1 || macro === -1 || !(m1 < macro && m2 < macro)) {
        throw new Error(`Microtask order invalid: ${JSON.stringify(timingResult.sequence)}`);
      }
      assertions.push({ name: 'microtask_drained_before_next_task', passed: true });

      if (typeof timingResult.rafTimestamp !== 'number' || timingResult.rafTimestamp <= 0) {
        throw new Error(`rAF timestamp invalid: ${timingResult.rafTimestamp}`);
      }
      assertions.push({ name: 'request_animation_frame_executed', passed: true });

      if (timingResult.timeoutFired || timingResult.rafFired) {
        throw new Error(`Cancelled timer or rAF fired: timeout=${timingResult.timeoutFired}, rAF=${timingResult.rafFired}`);
      }
      assertions.push({ name: 'timer_and_raf_cleanup_verified', passed: true });
      break;
    }

    case 'BR05': {
      await page.goto(`${serverOrigin}/index.html`);
      const urlResult = await page.evaluate(([p1, p2]) => {
        const raw = `${p2}/api/resource?query=val&filter=active#section-overview`;
        const u = new URL(raw);
        const locOrigin = window.location.origin;
        const otherOrigin = u.origin;

        return {
          protocol: u.protocol,
          hostname: u.hostname,
          port: u.port,
          pathname: u.pathname,
          searchParamQuery: u.searchParams.get('query'),
          searchParamFilter: u.searchParams.get('filter'),
          hash: u.hash,
          relative: new URL('../frame.html?mode=synthetic#target', `${p1}/nested/index.html`).href,
          relativeSameOrigin: new URL('./frame.html', p1).origin === locOrigin,
          locOrigin,
          otherOrigin,
          originsEqual: locOrigin === otherOrigin,
        };
      }, [serverOrigin, secondaryOrigin]);

      const p2Obj = new URL(secondaryOrigin);
      if (urlResult.protocol !== 'http:' ||
          urlResult.hostname !== '127.0.0.1' ||
          urlResult.port !== p2Obj.port ||
          urlResult.pathname !== '/api/resource' ||
          urlResult.searchParamQuery !== 'val' ||
          urlResult.hash !== '#section-overview') {
        throw new Error(`URL parsing components mismatch: ${JSON.stringify(urlResult)}`);
      }
      assertions.push({ name: 'url_components_parsed_accurately', passed: true });

      if (urlResult.originsEqual || urlResult.locOrigin === urlResult.otherOrigin) {
        throw new Error(`Origins on different ports must be distinct: ${urlResult.locOrigin} vs ${urlResult.otherOrigin}`);
      }
      assertions.push({ name: 'different_port_origin_distinct', passed: true });
      if (urlResult.relative !== `${serverOrigin}/frame.html?mode=synthetic#target` || !urlResult.relativeSameOrigin) {
        throw new Error('Relative URL/base resolution or same-origin positive control failed');
      }
      assertions.push({ name: 'relative_url_and_same_origin_control', passed: true });
      break;
    }

    case 'BR06': {
      await page.goto(`${serverOrigin}/index.html`);
      // Interception can suppress native preflight. Before removing it, install
      // a closed CSP for this synthetic page and exactly these local endpoints.
      await page.evaluate((origin) => {
        const policy = document.createElement('meta');
        policy.httpEquiv = 'Content-Security-Policy';
        const endpoints = ['cors-allow', 'cors-deny', 'cors-preflight-allow', 'cors-preflight-deny'];
        policy.content = "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src " + endpoints.map(p => `${origin}/${p}`).join(' ');
        document.head.appendChild(policy);
      }, secondaryOrigin);
      await context.unroute('**/*');
      const s2StartIdx = getServer2Requests().length;

      const corsResult = await page.evaluate(async (s2) => {
        // 1. CORS allow
        const resAllow = await fetch(`${s2}/cors-allow`);
        const dataAllow = await resAllow.json();

        // 2. CORS deny
        let denyThrew = false;
        try {
          await fetch(`${s2}/cors-deny`);
        } catch (error) {
          if (error.name !== 'TypeError') throw error;
          denyThrew = true;
        }

        // 3. CORS preflight success
        const resPreflight = await fetch(`${s2}/cors-preflight-allow`, {
          method: 'PUT',
          headers: {
            'X-Custom-Header': 'Qualified-Value',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ action: 'update' }),
        });
        const preflightData = await resPreflight.json();

        // 4. CORS preflight refusal
        let preflightRefused = false;
        try {
          await fetch(`${s2}/cors-preflight-deny`, {
            method: 'PUT',
            headers: { 'X-Disallowed-Header': 'Blocked' },
          });
        } catch (error) {
          if (error.name !== 'TypeError') throw error;
          preflightRefused = true;
        }

        // CSP counterpart: a valid local endpoint outside the connect allowlist
        // must not reach the server after routing is removed.
        let cspRefused = false;
        try { await fetch(`${s2}/credentials`); } catch (error) {
          if (error.name !== 'TypeError') throw error;
          cspRefused = true;
        }

        // 5. CORS opaque mode (no-cors)
        const resOpaque = await fetch(`${s2}/cors-deny`, { mode: 'no-cors' });

        return {
          allowSuccess: dataAllow.allowed === true,
          denyThrew,
          preflightSuccess: preflightData.preflightSuccess === true,
          preflightRefused,
          cspRefused,
          opaqueType: resOpaque.type,
          opaqueStatus: resOpaque.status,
        };
      }, secondaryOrigin);

      if (!corsResult.allowSuccess) throw new Error('CORS allow request failed');
      assertions.push({ name: 'cors_allow_success', passed: true });

      if (!corsResult.denyThrew) throw new Error('CORS deny request unexpectedly succeeded');

      // Server observation: CORS-denied GET actually sent
      const s2Observed = getServer2Requests().slice(s2StartIdx);
      const deniedGetReq = s2Observed.find((r) => r.path === '/cors-deny' && r.method === 'GET' && r.originMatch);
      if (!deniedGetReq) {
        throw new Error('Server did not observe CORS-denied GET request');
      }
      assertions.push({ name: 'cors_deny_refusal', passed: true });

      // Server observation: require server OPTIONS then allowed PUT
      const preflightAllowReqs = s2Observed.filter((r) => r.path === '/cors-preflight-allow');
      const optIdx = preflightAllowReqs.findIndex((r) => r.method === 'OPTIONS');
      const putIdx = preflightAllowReqs.findIndex((r) => r.method === 'PUT');
      if (optIdx === -1 || putIdx === -1 || optIdx >= putIdx) {
        throw new Error(`Expected server OPTIONS followed by PUT for preflight allow, got: ${JSON.stringify(preflightAllowReqs)}`);
      }
      if (!corsResult.preflightSuccess) throw new Error('CORS preflight request failed');
      assertions.push({ name: 'cors_preflight_success', passed: true });

      // Server observation: denied OPTIONS without PUT
      const preflightDenyReqs = s2Observed.filter((r) => r.path === '/cors-preflight-deny');
      const denyOptIdx = preflightDenyReqs.findIndex((r) => r.method === 'OPTIONS');
      const denyPutExists = preflightDenyReqs.some((r) => r.method === 'PUT');
      if (denyOptIdx === -1) {
        throw new Error('Server did not observe OPTIONS request for preflight deny');
      }
      if (denyPutExists) {
        throw new Error('Server unexpectedly observed PUT request after denied preflight OPTIONS');
      }
      if (!corsResult.preflightRefused) throw new Error('CORS preflight refusal unexpectedly succeeded');
      assertions.push({ name: 'cors_preflight_refusal', passed: true });

      if (corsResult.opaqueType !== 'opaque' || corsResult.opaqueStatus !== 0) {
        throw new Error(`CORS opaque response invalid: type=${corsResult.opaqueType}, status=${corsResult.opaqueStatus}`);
      }
      assertions.push({ name: 'cors_opaque_mode_success', passed: true });
      if (!corsResult.cspRefused || s2Observed.some(r => r.path === '/credentials')) {
        throw new Error('CSP failed to contain the un-intercepted synthetic fetch lane');
      }
      assertions.push({ name: 'unrouted_csp_request_containment', passed: true });
      break;
    }

    case 'BR07': {
      await page.goto(`${serverOrigin}/index.html`);
      const s2StartIdx = getServer2Requests().length;

      const fetchResult = await page.evaluate(async (s2) => {
        // 1. Fetch abort via AbortController
        const controller = new AbortController();
        controller.abort();
        let abortThrew = false;
        try {
          await fetch(`${s2}/cors-allow`, { signal: controller.signal });
        } catch (err) {
          if (err.name === 'AbortError') {
            abortThrew = true;
          } else { throw err; }
        }

        // 2. Fetch redirect followed
        const redirectRes = await fetch(`${s2}/redirect`);
        const redirectData = await redirectRes.json();
        const redirected = redirectRes.redirected;

        // 3. Set cookie on host 127.0.0.1 (not port-scoped)
        document.cookie = 'apg_auth_cred=synthetic_token_125; path=/';

        // Fetch with credentials: 'include' across ports
        const credRes = await fetch(`${s2}/credentials`, { credentials: 'include' });
        const credData = await credRes.json();

        // Fetch with credentials: 'omit' across ports
        const omitRes = await fetch(`${s2}/credentials`, { credentials: 'omit' });
        const omitData = await omitRes.json();

        return {
          abortThrew,
          redirected,
          redirectSuccess: redirectData.redirected === true,
          credHasSyntheticCookie: credData.hasSyntheticCookie === true,
          omitHasSyntheticCookie: omitData.hasSyntheticCookie === true,
        };
      }, secondaryOrigin);

      if (!fetchResult.abortThrew) throw new Error('Fetch abort failed to reject with AbortError');
      assertions.push({ name: 'fetch_abort_controller_cancellation', passed: true });

      // Server observation: redirect sequence /redirect then /redirect-target
      const s2Observed = getServer2Requests().slice(s2StartIdx);
      const redirReqIdx = s2Observed.findIndex((r) => r.path === '/redirect');
      const targetReqIdx = s2Observed.findIndex((r) => r.path === '/redirect-target');
      if (redirReqIdx === -1 || targetReqIdx === -1 || redirReqIdx >= targetReqIdx) {
        throw new Error(`Server did not observe redirect sequence /redirect then /redirect-target: ${JSON.stringify(s2Observed)}`);
      }
      if (!fetchResult.redirected || !fetchResult.redirectSuccess) {
        throw new Error('Fetch redirect failed');
      }
      assertions.push({ name: 'fetch_redirect_followed_successfully', passed: true });

      // Server observation: credentials include vs omit
      const credReqs = s2Observed.filter((r) => r.path === '/credentials');
      if (credReqs.length < 2) {
        throw new Error(`Expected at least 2 /credentials server observations, got ${credReqs.length}`);
      }
      const includeObserved = credReqs[0].hasSyntheticCookie === true;
      const omitObserved = credReqs[1].hasSyntheticCookie === false;

      if (!includeObserved || !fetchResult.credHasSyntheticCookie) {
        throw new Error('Host-scoped cookie was not included in cross-port credentials fetch');
      }
      assertions.push({ name: 'fetch_credentials_included_and_observed', passed: true });

      if (!omitObserved || fetchResult.omitHasSyntheticCookie) {
        throw new Error('Cookie was unexpectedly included when credentials were omitted');
      }
      assertions.push({ name: 'fetch_credentials_omitted_observed', passed: true });
      break;
    }

    case 'BR08': {
      await page.goto(`${serverOrigin}/index.html`);
      await page.evaluate(() => {
        localStorage.setItem('br08_persist_key', 'persisted_value');
        sessionStorage.setItem('br08_session_key', 'session_tab_1');
      });

      await page.reload();
      const reloadData = await page.evaluate(() => ({
        local: localStorage.getItem('br08_persist_key'),
        session: sessionStorage.getItem('br08_session_key'),
      }));
      if (reloadData.local !== 'persisted_value' || reloadData.session !== 'session_tab_1') {
        throw new Error(`Persistence failed on reload: ${JSON.stringify(reloadData)}`);
      }
      assertions.push({ name: 'local_storage_persistence_and_reload', passed: true });

      const peerResult = await page.evaluate(async () => {
        const iframe = document.createElement('iframe');
        iframe.src = '/frame.html';
        document.body.appendChild(iframe);
        await new Promise((resolve) => { iframe.onload = resolve; });

        let eventDetail = null;
        iframe.contentWindow.addEventListener('storage', (e) => {
          eventDetail = { key: e.key, oldValue: e.oldValue, newValue: e.newValue };
        });

        localStorage.setItem('br08_persist_key', 'mutated_by_parent');
        for (let i = 0; i < 25 && !eventDetail; i++) {
          await new Promise((resolve) => setTimeout(resolve, 20));
        }

        const iframeLocalVal = iframe.contentWindow.localStorage.getItem('br08_persist_key');
        iframe.remove();

        return {
          eventDetail,
          iframeLocalVal,
        };
      });

      if (!peerResult.eventDetail || peerResult.eventDetail.key !== 'br08_persist_key' || peerResult.eventDetail.newValue !== 'mutated_by_parent') {
        throw new Error(`Storage event mismatch: ${JSON.stringify(peerResult)}`);
      }
      assertions.push({ name: 'local_storage_peer_event_observed', passed: true });

      const page2 = await context.newPage();
      try {
        await page2.goto(`${serverOrigin}/index.html`);
        const page2Session = await page2.evaluate(() => sessionStorage.getItem('br08_session_key'));
        const page2Local = await page2.evaluate(() => localStorage.getItem('br08_persist_key'));
        if (page2Session !== null) {
          throw new Error(`sessionStorage leaked to independent page: ${page2Session}`);
        }
        if (page2Local !== 'mutated_by_parent') {
          throw new Error(`localStorage not visible in second page: ${page2Local}`);
        }
        assertions.push({ name: 'session_storage_context_isolation', passed: true });
      } finally {
        await page2.close();
      }
      break;
    }

    case 'BR09': {
      await page.goto(`${serverOrigin}/index.html`);
      const historyResult = await page.evaluate(async () => {
        // Set same-document marker
        window.__sameDocMarker = 'retained_history_marker';

        const events = [];
        window.addEventListener('popstate', (e) => {
          events.push({ type: 'popstate', state: e.state });
        });
        window.addEventListener('hashchange', (e) => {
          events.push({ type: 'hashchange', newURL: e.newURL });
        });

        history.pushState({ step: 1 }, 'Step 1', '/index.html?step=1');
        const path1 = window.location.search;

        history.replaceState({ step: 2 }, 'Step 2', '/index.html?step=2');
        const path2 = window.location.search;

        history.pushState({ step: 3 }, 'Step 3', '/index.html?step=3');

        history.back();
        await new Promise((resolve) => setTimeout(resolve, 50));

        location.hash = '#view-hash';
        await new Promise((resolve) => setTimeout(resolve, 50));

        return {
          path1,
          path2,
          events,
          sameDocMarker: window.__sameDocMarker,
        };
      });

      if (historyResult.path1 !== '?step=1' || historyResult.path2 !== '?step=2') {
        throw new Error(`history push/replace path mismatch: ${historyResult.path1}, ${historyResult.path2}`);
      }
      if (historyResult.sameDocMarker !== 'retained_history_marker') {
        throw new Error('Same-document marker was lost during History API navigation');
      }
      assertions.push({ name: 'history_push_replace_state_updates_location', passed: true });

      const popstateEvt = historyResult.events.find((e) => e.type === 'popstate');
      if (!popstateEvt || !popstateEvt.state || popstateEvt.state.step !== 2) {
        throw new Error(`popstate event mismatch: ${JSON.stringify(popstateEvt)}`);
      }
      assertions.push({ name: 'popstate_event_restores_state', passed: true });

      const hashEvt = historyResult.events.find((e) => e.type === 'hashchange');
      if (!hashEvt || !hashEvt.newURL.includes('#view-hash')) {
        throw new Error(`hashchange event mismatch: ${JSON.stringify(hashEvt)}`);
      }
      assertions.push({ name: 'hashchange_event_fired', passed: true });

      // Actual cross-document Location.assign allowed route: old marker gone, route updated
      await page.evaluate((url) => {
        location.assign(url);
      }, `${serverOrigin}/frame.html`);
      await page.waitForURL(`${serverOrigin}/frame.html`);

      const crossDocResult = await page.evaluate(() => {
        return {
          oldMarker: window.__sameDocMarker,
          pathname: window.location.pathname,
        };
      });

      if (crossDocResult.oldMarker !== undefined) {
        throw new Error(`Old window marker retained across cross-document Location.assign: ${crossDocResult.oldMarker}`);
      }
      if (crossDocResult.pathname !== '/frame.html') {
        throw new Error(`Cross-document navigation location mismatch: expected /frame.html, got ${crossDocResult.pathname}`);
      }
      break;
    }

    case 'BR10': {
      await page.goto(`${serverOrigin}/index.html`);
      const ceResult = await page.evaluate(() => {
        let connectedFired = false;
        let attributeChangedFired = false;

        if (!customElements.get('test-component-br10')) {
          class TestComponent extends HTMLElement {
            static get observedAttributes() { return ['title']; }
            constructor() {
              super();
              this.attachShadow({ mode: 'open' });
              this.shadowRoot.innerHTML = `
                <style>
                  .shadow-inner { color: red; }
                </style>
                <div class="shadow-inner" id="shadow-box">Shadow Content</div>
                <slot id="slot-target"></slot>
              `;
            }
            connectedCallback() { connectedFired = true; }
            attributeChangedCallback(name, oldVal, newVal) {
              if (name === 'title') attributeChangedFired = true;
            }
          }
          customElements.define('test-component-br10', TestComponent);
        }

        const host = document.getElementById('br10-host');
        host.innerHTML = '';
        const elem = document.createElement('test-component-br10');
        elem.setAttribute('title', 'Initial Title');
        const slottedChild = document.createElement('span');
        slottedChild.id = 'slotted-content';
        slottedChild.textContent = 'Projected Text';
        elem.appendChild(slottedChild);
        host.appendChild(elem);

        const lifecyclePassed = connectedFired && attributeChangedFired;
        const queryInDoc = document.querySelector('#shadow-box');
        const queryInShadow = elem.shadowRoot.querySelector('#shadow-box');
        const encapsulationPassed = queryInDoc === null && queryInShadow !== null;

        const slot = elem.shadowRoot.querySelector('#slot-target');
        const assigned = slot.assignedNodes();
        const slotPassed = assigned.length > 0 && assigned[0].textContent === 'Projected Text';

        return { lifecyclePassed, encapsulationPassed, slotPassed };
      });

      if (!ceResult.lifecyclePassed) throw new Error('Custom element lifecycle callbacks failed');
      assertions.push({ name: 'custom_element_lifecycle_executed', passed: true });

      if (!ceResult.encapsulationPassed) throw new Error('Shadow DOM encapsulation failed');
      assertions.push({ name: 'shadow_dom_style_and_dom_encapsulation', passed: true });

      if (!ceResult.slotPassed) throw new Error('Slot projection resolution failed');
      assertions.push({ name: 'slot_content_projection_resolved', passed: true });
      break;
    }

    case 'BR11': {
      await page.goto(`${serverOrigin}/index.html`);
      const geomResult = await page.evaluate(() => {
        const box = document.getElementById('br11-box');
        const scrollEl = document.getElementById('br11-scroll');

        const computed = window.getComputedStyle(box);
        const bgColor = computed.backgroundColor;
        const display = computed.display;

        const rect = box.getBoundingClientRect();

        const initialScrollTop = scrollEl.scrollTop;
        const scrollHeight = scrollEl.scrollHeight;
        const clientHeight = scrollEl.clientHeight;
        scrollEl.scrollTop = 40;
        const updatedScrollTop = scrollEl.scrollTop;

        return {
          bgColor,
          display,
          width: rect.width,
          height: rect.height,
          initialScrollTop,
          scrollHeight,
          clientHeight,
          updatedScrollTop,
        };
      });

      if (geomResult.bgColor.replace(/\s+/g, '') !== 'rgb(0,128,255)' || geomResult.display !== 'block') {
        throw new Error(`Computed style mismatch: ${JSON.stringify(geomResult)}`);
      }
      assertions.push({ name: 'computed_style_values_resolved', passed: true });

      if (Math.round(geomResult.width) !== 200 || Math.round(geomResult.height) !== 100) {
        throw new Error(`Bounding client rect mismatch: width=${geomResult.width}, height=${geomResult.height}`);
      }
      assertions.push({ name: 'bounding_client_rect_dimensions_accurate', passed: true });

      if (geomResult.scrollHeight <= geomResult.clientHeight || geomResult.updatedScrollTop <= 0) {
        throw new Error(`Scroll metrics inconsistent: ${JSON.stringify(geomResult)}`);
      }
      assertions.push({ name: 'scroll_geometry_metrics_consistent', passed: true });
      break;
    }

    case 'BR12': {
      await page.goto(`${serverOrigin}/index.html`);
      const s1StartIdx = getServer1Requests().length;

      const workerResult = await page.evaluate(async (s1) => {
        const worker = new Worker(`${s1}/worker.js`);

        const msgPromise = new Promise((resolve, reject) => {
          const timer = setTimeout(() => reject(new Error('Worker message timeout')), 3000);
          worker.onmessage = (e) => {
            clearTimeout(timer);
            resolve(e.data);
          };
          worker.onerror = (e) => {
            clearTimeout(timer);
            reject(new Error(e.message || 'Worker error'));
          };
        });

        worker.postMessage({ type: 'compute', a: 6, b: 7 });
        const reply = await msgPromise;

        worker.terminate();

        let replyAfterTerminate = false;
        worker.onmessage = () => { replyAfterTerminate = true; };
        worker.postMessage({ type: 'compute', a: 10, b: 10 });

        await new Promise((resolve) => setTimeout(resolve, 60));

        return {
          replyValue: reply.value,
          replyAfterTerminate,
        };
      }, serverOrigin);

      // Primary server observation for worker script (actual allowlist server request)
      const s1Observed = getServer1Requests().slice(s1StartIdx);
      const workerObserved = s1Observed.some((r) => r.path === '/worker.js' && r.method === 'GET');
      if (!workerObserved) {
        throw new Error('Primary server did not observe actual allowlist request for /worker.js');
      }

      if (workerResult.replyValue !== 42) {
        throw new Error(`Worker computation mismatch: expected 42, got ${workerResult.replyValue}`);
      }
      assertions.push({ name: 'worker_bidirectional_messaging', passed: true });

      if (workerResult.replyAfterTerminate) {
        throw new Error('Worker processed message after terminate()');
      }
      assertions.push({ name: 'worker_post_termination_message_absent', passed: true });
      break;
    }

    case 'BR13': {
      await page.goto(`${serverOrigin}/index.html`);
      const s1StartIdx = getServer1Requests().length;

      const moduleResult = await page.evaluate(async (s1) => {
        const mod = await import(`${s1}/module.js`);
        const greeting = mod.getGreeting('APG125');
        const compute = mod.COMPUTE_RESULT;

        let refused = false;
        try {
          await import(`${s1}/refused-module.js`);
        } catch (error) {
          if (error.name !== 'TypeError') throw error;
          refused = true;
        }

        return {
          moduleLoaded: mod.MODULE_LOADED === true,
          compute,
          greeting,
          refused,
        };
      }, serverOrigin);

      // Primary server observation for module, submodule, and refused-module
      const s1Observed = getServer1Requests().slice(s1StartIdx);
      const modObserved = s1Observed.some((r) => r.path === '/module.js' && r.method === 'GET');
      const submodObserved = s1Observed.some((r) => r.path === '/submodule.js' && r.method === 'GET');
      const refusedObserved = s1Observed.some((r) => r.path === '/refused-module.js' && r.method === 'GET');
      if (!modObserved || !submodObserved || !refusedObserved) {
        throw new Error(`Primary server did not observe module requests: mod=${modObserved}, submod=${submodObserved}, refused=${refusedObserved}`);
      }

      if (!moduleResult.moduleLoaded || moduleResult.compute !== 84) {
        throw new Error(`Module loading failed: ${JSON.stringify(moduleResult)}`);
      }
      assertions.push({ name: 'module_static_and_dynamic_import_success', passed: true });

      if (!moduleResult.refused) {
        throw new Error('Disallowed module resource unexpectedly succeeded without refusal');
      }
      assertions.push({ name: 'module_missing_resource_refusal', passed: true });
      break;
    }

    case 'BR14': {
      await page.goto(`${serverOrigin}/index.html`);
      const blobResult = await page.evaluate(async () => {
        const payload = 'synthetic-blob-content-apg125';
        const blob = new Blob([payload], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);

        const res = await fetch(url);
        const text = await res.text();

        URL.revokeObjectURL(url);

        let fetchAfterRevokeFailed = false;
        try {
          await fetch(url);
        } catch (error) {
          if (error.name !== 'TypeError') throw error;
          fetchAfterRevokeFailed = true;
        }

        return {
          isBlobUrl: url.startsWith('blob:'),
          textMatches: text === payload,
          fetchAfterRevokeFailed,
        };
      });

      if (!blobResult.isBlobUrl || !blobResult.textMatches) {
        throw new Error(`Blob URL read failed: ${JSON.stringify(blobResult)}`);
      }
      assertions.push({ name: 'blob_url_creation_and_read_success', passed: true });

      if (!blobResult.fetchAfterRevokeFailed) {
        throw new Error('Fetch of revoked blob URL unexpectedly succeeded');
      }
      assertions.push({ name: 'blob_url_revocation_refusal', passed: true });
      break;
    }

    default:
      throw new Error(`Unknown scenario ID: ${scenarioId}`);
  }

  return { assertions, artifacts };
}

// Await every acquired server; a secondary cleanup error must not replace
// the initiating failure or expose unsanitized diagnostics.
export async function closeServers(servers, initiatingError = null) {
  const results = await Promise.allSettled(servers.filter(Boolean).map(server =>
    new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve()))));
  const failures = results.filter(result => result.status === 'rejected').map(result => result.reason);
  if (!failures.length) return;
  if (!initiatingError) throw failures[0];
  for (const failure of failures) {
    console.error('Server cleanup failure suppressed to preserve initiating failure:', JSON.stringify(sanitizeError(failure)));
  }
}

export async function main(customArgs = null) {
  const cliArgs = customArgs || process.argv.slice(2);
  const custody = validateRunnerCustody(cliArgs);
  scratchDir = custody.scratchDir;
  artifactsDir = custody.artifactsDir;
  const {
    receiptPath,
    requestedBrowsers,
    requestedGroup,
    scenarioFilter,
    tablePath,
    registerPath,
  } = custody;

  // Load and validate active family table and scenarios register before execution
  const activeFamilyTable = tablePath ? JSON.parse(fs.readFileSync(tablePath, 'utf-8')) : familyTable;
  const activeRegister = registerPath ? JSON.parse(fs.readFileSync(registerPath, 'utf-8')) : scenariosManifest;

  validateFamilyTable(activeFamilyTable);
  validateFamilyTableAndRegister(activeFamilyTable, activeRegister);

  // Validate requestedGroup
  if (!activeFamilyTable.aliases || !activeFamilyTable.aliases[requestedGroup]) {
    throw new Error(`Unknown scenario group / alias: ${requestedGroup}`);
  }
  const aliasScenarios = new Set(activeFamilyTable.aliases[requestedGroup]);

  // If scenarioFilter provided, validate all IDs exist in family table
  const tableIds = new Set(activeFamilyTable.entries.map((e) => e.id));
  if (scenarioFilter) {
    for (const scId of scenarioFilter) {
      if (!tableIds.has(scId)) {
        throw new Error(`Unknown scenario ID: ${scId}`);
      }
    }
  }

  // Determine exact target scenario IDs to run
  const targetScenarioIds = [];
  for (const sc of activeRegister.scenarios) {
    if (requestedGroup !== 'all' && !aliasScenarios.has(sc.id)) {
      continue;
    }
    if (scenarioFilter && !scenarioFilter.has(sc.id)) {
      continue;
    }
    targetScenarioIds.push(sc.id);
  }

  if (targetScenarioIds.length === 0) {
    throw new Error('No matching scenarios to execute');
  }

  // Resolve authority ONCE BEFORE execution
  const resolvedAuthority = resolveScenarioAuthority(activeFamilyTable, targetScenarioIds);

  // Ensure artifacts directory exists inside scratch with mode 0700
  fs.mkdirSync(artifactsDir, { recursive: true, mode: 0o700 });
  const artStat = fs.lstatSync(artifactsDir);
  if (artStat.isSymbolicLink() || fs.realpathSync(artifactsDir) !== artifactsDir) {
    throw new Error(`Artifacts directory must not be a symlink: ${artifactsDir}`);
  }

  // Resolve Playwright packages dynamically before browser launch
  const packageRoot = process.env.APG_PLAYWRIGHT_PACKAGE_ROOT;
  const lookupDir = (packageRoot && fs.existsSync(path.join(packageRoot, 'node_modules')))
    ? packageRoot
    : scratchDir;
  const requireFromScratch = createRequire(path.join(lookupDir, 'runner.js'));

  let playwrightPkg;
  let playwrightTestPkg;
  try {
    playwrightPkg = requireFromScratch('playwright');
    playwrightTestPkg = requireFromScratch('@playwright/test');
  } catch (err) {
    throw new Error(`Failed to load Playwright packages from scratch runtime: ${err.message}`);
  }

  chromium = playwrightPkg.chromium;
  firefox = playwrightPkg.firefox;
  webkit = playwrightPkg.webkit;
  expect = playwrightTestPkg.expect;
  BROWSER_ENGINES = { chromium, firefox, webkit };

  const startTime = Date.now();
  let server1 = null;
  let server2 = null;
  let initiatingError = null;
  let getServer1Requests = () => [];
  let getServer2Requests = () => [];
  let server1Origin = null;
  let server2Origin = null;
  const platform = process.platform;

  const browserVersions = {};
  const browserEnvironments = {};
  const executedScenarios = [];
  const allArtifacts = new Set();

  try {
    const s1Res = await startServer();
    server1 = s1Res.server;
    server1Origin = s1Res.origin;
    getServer1Requests = s1Res.getObservedRequests;

    const s2Res = await startSecondaryServer(server1Origin);
    server2 = s2Res.server;
    server2Origin = s2Res.origin;
    getServer2Requests = s2Res.getObservedRequests;

    for (const browserName of requestedBrowsers) {
      const engine = BROWSER_ENGINES[browserName];
      if (!engine) {
        throw new Error(`Unsupported browser engine: ${browserName}`);
      }

      const browser = await engine.launch({ headless: true });
      try {
        const actualVersion = browser.version();
        browserVersions[browserName] = actualVersion;

        // Query UA and capture browser environment features
        const uaContext = await createSecureContext(browser, server1Origin, server2Origin);
        const uaPage = await uaContext.newPage();
        await uaPage.goto(`${server1Origin}/index.html`);
        const envDetection = await uaPage.evaluate(() => {
          return {
            userAgent: navigator.userAgent,
            windowOrigin: window.origin || window.location.origin,
            features: {
              customElements: typeof window.customElements !== 'undefined',
              shadowDOM: typeof Element.prototype.attachShadow === 'function',
              Worker: typeof window.Worker === 'function',
              MutationObserver: typeof window.MutationObserver === 'function',
              localStorage: (() => {
                try { return typeof window.localStorage !== 'undefined' && window.localStorage !== null; } catch { return false; }
              })(),
              sessionStorage: (() => {
                try { return typeof window.sessionStorage !== 'undefined' && window.sessionStorage !== null; } catch { return false; }
              })(),
              fetch: typeof window.fetch === 'function',
              requestAnimationFrame: typeof window.requestAnimationFrame === 'function',
            },
          };
        });
        await uaContext.close();

        browserEnvironments[browserName] = {
          engine: browserName,
          version: actualVersion,
          user_agent: envDetection.userAgent,
          platform: process.platform,
          arch: process.arch,
          os_release: os.release(),
          origin_role: 'primary',
          window_origin_role: 'primary',
          window_origin: envDetection.windowOrigin,
          headless: true,
          context: {
            service_workers: 'block',
            viewport: { width: 1280, height: 720 },
          },
          features: envDetection.features,
        };

        const scenariosToRun = activeRegister.scenarios.filter((sc) => targetScenarioIds.includes(sc.id));

        for (const sc of scenariosToRun) {
          const scStart = Date.now();
          const context = await createSecureContext(browser, server1Origin, server2Origin);
          const page = await context.newPage();

          let status = 'passed';
          let errMessage = null;
          let errDetails = null;
          let assertions = [];
          let artifacts = [];
          let caughtErr = null;

          try {
            const result = await executeScenario(sc.id, browserName, page, context, server1Origin, server2Origin, platform, {
              getServer1Requests,
              getServer2Requests,
            });
            assertions = result.assertions;
            artifacts = result.artifacts;
            artifacts.forEach((a) => allArtifacts.add(a));
          } catch (err) {
            status = 'failed';
            caughtErr = err;
            errDetails = sanitizeError(err);
            errMessage = errDetails.message;
          } finally {
            await context.close();
          }

          const scDuration = Date.now() - scStart;
          executedScenarios.push({
            scenario_id: sc.id,
            group: sc.group,
            browser: browserName,
            status,
            duration_ms: scDuration,
            assertions,
            artifacts,
            error: errMessage,
            error_details: errDetails,
          });

          if (status === 'failed') {
            writeReceiptFile(receiptPath, executedScenarios, browserVersions, startTime, artifactsDir, allArtifacts, activeRegister, browserEnvironments, resolvedAuthority, tablePath, registerPath);
            const failureErr = new Error(`Scenario ${sc.id} failed on ${browserName}: ${errMessage}`);
            failureErr.name = errDetails.class;
            if (caughtErr && caughtErr.cause) {
              failureErr.cause = caughtErr.cause;
            }
            throw failureErr;
          }
        }
      } finally {
        await browser.close();
      }
    }
  } catch (err) {
    initiatingError = err;
    throw err;
  } finally {
    await closeServers([server1, server2], initiatingError);
  }

  const receipt = writeReceiptFile(receiptPath, executedScenarios, browserVersions, startTime, artifactsDir, allArtifacts, activeRegister, browserEnvironments, resolvedAuthority, tablePath, registerPath);
  console.log(JSON.stringify({
    status: receipt.summary.failed === 0 ? 'SUCCESS' : 'FAILURE',
    summary: receipt.summary,
    browsers: receipt.browsers,
    receiptPath,
  }));

  if (receipt.summary.failed > 0) {
    process.exit(1);
  }
}

const isDirectExecution = () => {
  if (!process.argv[1]) return false;
  try {
    return fs.realpathSync(fileURLToPath(import.meta.url)) === fs.realpathSync(process.argv[1]);
  } catch {
    return false;
  }
};

if (isDirectExecution()) {
  main().catch((err) => {
    let diagnostic;
    try {
      diagnostic = sanitizeError(err);
    } catch {
      diagnostic = {
        class: (err && err.name) || 'Error',
        message: sanitizeDiagnosticText(err && err.message ? err.message : String(err)),
        cause: null,
      };
    }
    console.error('Runner fatal error:', JSON.stringify(diagnostic));
    process.exit(1);
  });
}
