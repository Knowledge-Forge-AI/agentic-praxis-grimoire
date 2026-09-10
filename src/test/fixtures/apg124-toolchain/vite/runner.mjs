#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import crypto from 'node:crypto';

// Parse arguments
const args = process.argv.slice(2);
let scratchRoot = '';
let packageRoot = '';
let scenarioFilter = null;
let outputFile = null;

for (let i = 0; i < args.length; i++) {
  if (args[i] === '--scratch-root' && args[i + 1]) {
    scratchRoot = path.resolve(args[++i]);
  } else if (args[i] === '--package-root' && args[i + 1]) {
    packageRoot = path.resolve(args[++i]);
  } else if (args[i] === '--filter' && args[i + 1]) {
    scenarioFilter = args[++i].split(',').map(s => s.trim());
  } else if (args[i] === '--output' && args[i + 1]) {
    outputFile = path.resolve(args[++i]);
  }
}

// Fail closed if scratch root is not explicitly provided
if (!scratchRoot) {
  scratchRoot = process.env.APG_VITE_OWNED_SCRATCH_ROOT || '';
}
if (!scratchRoot) {
  console.error('Missing required scratch root: provide --scratch-root or set APG_VITE_OWNED_SCRATCH_ROOT');
  process.exit(1);
}
if (!path.isAbsolute(scratchRoot)) {
  console.error('Scratch root must be an absolute path:', scratchRoot);
  process.exit(1);
}
if (!fs.existsSync(scratchRoot)) {
  console.error('Scratch root does not exist:', scratchRoot);
  process.exit(1);
}

const scratchStat = fs.lstatSync(scratchRoot);
if (scratchStat.isSymbolicLink() || !scratchStat.isDirectory()) {
  console.error('Scratch root must be a directory and not a symlink:', scratchRoot);
  process.exit(1);
}
if (typeof process.getuid === 'function' && scratchStat.uid !== process.getuid()) {
  console.error(`Scratch root must be owned by caller (uid ${process.getuid()}), got uid ${scratchStat.uid}`);
  process.exit(1);
}
const scratchMode = scratchStat.mode & 0o777;
if (scratchMode !== 0o700) {
  console.error(`Scratch root must be mode 0700, got: 0${scratchMode.toString(8)}`);
  process.exit(1);
}

let scratchReal;
try {
  scratchReal = fs.realpathSync(scratchRoot);
} catch (err) {
  console.error('Failed to resolve scratch root realpath:', err.message);
  process.exit(1);
}
if (scratchReal !== scratchRoot) {
  console.error(`Scratch root must be a direct path without symlinks: ${scratchRoot} -> ${scratchReal}`);
  process.exit(1);
}

// Validate package root
if (!packageRoot) {
  packageRoot = process.env.APG_VITE_PACKAGE_ROOT || '';
}
if (!packageRoot) {
  console.error('Missing required package root: provide --package-root or set APG_VITE_PACKAGE_ROOT');
  process.exit(1);
}
if (!path.isAbsolute(packageRoot)) {
  console.error('Package root must be an absolute path:', packageRoot);
  process.exit(1);
}
if (!fs.existsSync(packageRoot)) {
  console.error('Package root does not exist:', packageRoot);
  process.exit(1);
}

const pkgStat = fs.lstatSync(packageRoot);
if (pkgStat.isSymbolicLink() || !pkgStat.isDirectory()) {
  console.error('Package root must be a directory and not a symlink:', packageRoot);
  process.exit(1);
}

let pkgReal;
try {
  pkgReal = fs.realpathSync(packageRoot);
} catch (err) {
  console.error('Failed to resolve package root realpath:', err.message);
  process.exit(1);
}
if (pkgReal !== packageRoot) {
  console.error(`Package root must be a direct path without symlinks: ${packageRoot} -> ${pkgReal}`);
  process.exit(1);
}

if (!pkgReal.startsWith(scratchReal + path.sep) && pkgReal !== scratchReal) {
  console.error('Package root must be strictly inside owned scratch root');
  process.exit(1);
}

// Output constrained within scratch
if (outputFile) {
  const outputResolved = path.resolve(outputFile);
  if (!outputResolved.startsWith(scratchReal + path.sep)) {
    console.error('Output file must be constrained within scratch root:', outputResolved);
    process.exit(1);
  }
  let curr = path.dirname(outputResolved);
  while (curr && curr !== scratchReal && curr !== path.dirname(curr)) {
    if (fs.existsSync(curr)) {
      const st = fs.lstatSync(curr);
      if (st.isSymbolicLink()) {
        console.error('Output path contains symlink component:', curr);
        process.exit(1);
      }
      if (fs.realpathSync(curr) !== curr) {
        console.error('Output path component must be direct without symlinks:', curr);
        process.exit(1);
      }
    }
    curr = path.dirname(curr);
  }
}

// No artifacts before validated scratch; now check vite entry
const viteEntry = path.join(pkgReal, 'node_modules', 'vite', 'dist', 'node', 'index.js');
if (!fs.existsSync(viteEntry)) {
  console.error('Vite entrypoint not found at:', viteEntry);
  process.exit(1);
}

const vite = await import(viteEntry);
const { createServer, build, preview, resolveConfig, loadEnv } = vite;

function sha256File(filePath) {
  const content = fs.readFileSync(filePath);
  return crypto.createHash('sha256').update(content).digest('hex');
}

function httpGet(hostname, port, requestPath) {
  return new Promise((resolve, reject) => {
    const req = http.get({ host: hostname, port, path: requestPath }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, data }));
    });
    req.on('error', reject);
    req.setTimeout(5000, () => {
      req.destroy(new Error('HTTP request timed out'));
    });
  });
}

function getAllFiles(dirPath, arrayOfFiles = [], baseDir = dirPath) {
  const files = fs.readdirSync(dirPath);
  for (const file of files) {
    const fullPath = path.join(dirPath, file);
    if (fs.statSync(fullPath).isDirectory()) {
      getAllFiles(fullPath, arrayOfFiles, baseDir);
    } else {
      arrayOfFiles.push(path.relative(baseDir, fullPath));
    }
  }
  return arrayOfFiles.sort();
}

// Unique run dir mode 0700, existing tmp ancestor safe
const tmpDir = path.join(scratchReal, 'tmp');
if (!fs.existsSync(tmpDir)) {
  fs.mkdirSync(tmpDir, { mode: 0o700 });
} else {
  const tmpStat = fs.lstatSync(tmpDir);
  if (tmpStat.isSymbolicLink() || !tmpStat.isDirectory()) {
    console.error('Existing tmp ancestor must be a directory and not a symlink');
    process.exit(1);
  }
  if (typeof process.getuid === 'function' && tmpStat.uid !== process.getuid()) {
    console.error('Existing tmp ancestor must be owned by caller');
    process.exit(1);
  }
  if (fs.realpathSync(tmpDir) !== tmpDir) {
    console.error('Existing tmp ancestor must not contain symlinks');
    process.exit(1);
  }
  try {
    fs.chmodSync(tmpDir, 0o700);
  } catch {}
}

const runId = 'apg124-run-' + Date.now() + '-' + crypto.randomBytes(4).toString('hex');
const runDir = path.join(tmpDir, runId);
fs.mkdirSync(runDir, { mode: 0o700 });

const results = [];
const allScenarios = [
  'VITE01', 'VITE02', 'VITE03', 'VITE04', 'VITE05', 'VITE06',
  'VITE07', 'VITE08', 'VITE09', 'VITE10', 'VITE11', 'VITE12'
];

const targetScenarios = scenarioFilter
  ? allScenarios.filter(s => scenarioFilter.includes(s))
  : allScenarios;

function prepareScenarioDir(scId) {
  const scDir = path.join(runDir, scId);
  fs.mkdirSync(scDir, { recursive: true, mode: 0o700 });
  return scDir;
}

try {
  // Scenario VITE01: Resolved Config
  if (targetScenarios.includes('VITE01')) {
    const start = Date.now();
    const scDir = prepareScenarioDir('VITE01');
    fs.mkdirSync(path.join(scDir, 'public'), { recursive: true });
    fs.writeFileSync(path.join(scDir, 'index.html'), '<html><body>VITE01</body></html>');
    
    const conf = await resolveConfig({
      root: scDir,
      base: '/app-base',
      mode: 'production',
      build: { outDir: path.join(scDir, 'custom-dist') }
    }, 'build');

    const assertions = [
      { name: 'resolved_root_exact', passed: path.resolve(conf.root) === path.resolve(scDir) },
      { name: 'base_normalized', passed: conf.base === '/app-base/' },
      { name: 'public_dir_resolved', passed: path.resolve(conf.publicDir) === path.resolve(scDir, 'public') },
      { name: 'build_command_assigned', passed: conf.command === 'build' && conf.mode === 'production' }
    ];

    results.push({
      scenario_id: 'VITE01',
      name: 'resolved_config',
      status: assertions.every(a => a.passed) ? 'passed' : 'failed',
      duration_ms: Date.now() - start,
      assertions,
      error: null
    });
  }

  // Scenario VITE02: Env Secrecy and Exposure
  if (targetScenarios.includes('VITE02')) {
    const start = Date.now();
    const scDir = prepareScenarioDir('VITE02');
    fs.mkdirSync(path.join(scDir, 'src'), { recursive: true });
    fs.writeFileSync(path.join(scDir, '.env'), ['VITE_EXPOSED_SECRET=apg124_public_key_998', 'PRIVATE_DATABASE_TOKEN=super_private_token_441', ''].join(String.fromCharCode(10)));
    
    const env = loadEnv('production', scDir, 'VITE_');
    const vitePrefixExposed = env.VITE_EXPOSED_SECRET === 'apg124_public_key_998';
    const secretSuppressed = env.PRIVATE_DATABASE_TOKEN === undefined;

    fs.writeFileSync(path.join(scDir, 'index.html'), '<html><body><script type="module" src="/src/main.js"></script></body></html>');
    fs.writeFileSync(path.join(scDir, 'src', 'main.js'), 'console.log(import.meta.env.VITE_EXPOSED_SECRET); console.log(import.meta.env.PRIVATE_DATABASE_TOKEN);');

    const outDir = path.join(scDir, 'dist');
    await build({
      root: scDir,
      logLevel: 'silent',
      build: { outDir, emptyOutDir: true }
    });

    const distFiles = getAllFiles(outDir);
    const jsFiles = distFiles.filter(f => f.endsWith('.js'));
    let clientBundleSecretAbsent = true;
    let clientBundlePublicPresent = false;

    for (const jsFile of jsFiles) {
      const c = fs.readFileSync(path.join(outDir, jsFile), 'utf-8');
      if (c.includes('super_private_token_441')) clientBundleSecretAbsent = false;
      if (c.includes('apg124_public_key_998')) clientBundlePublicPresent = true;
    }

    const assertions = [
      { name: 'vite_prefix_env_exposed', passed: vitePrefixExposed && clientBundlePublicPresent },
      { name: 'secret_env_suppressed', passed: secretSuppressed },
      { name: 'client_bundle_secret_absent', passed: clientBundleSecretAbsent }
    ];

    results.push({
      scenario_id: 'VITE02',
      name: 'env_secrecy_and_exposure',
      status: assertions.every(a => a.passed) ? 'passed' : 'failed',
      duration_ms: Date.now() - start,
      assertions,
      error: null
    });
  }

  // Scenario VITE03: Asset & PublicDir & CSS & Alias
  if (targetScenarios.includes('VITE03')) {
    const start = Date.now();
    const scDir = prepareScenarioDir('VITE03');
    fs.mkdirSync(path.join(scDir, 'src'), { recursive: true });
    fs.mkdirSync(path.join(scDir, 'public'), { recursive: true });

    fs.writeFileSync(path.join(scDir, 'public', 'robots.txt'), ['User-agent: *', 'Disallow: /'].join(String.fromCharCode(10)));
    fs.writeFileSync(path.join(scDir, 'src', 'theme.css'), 'body { background-color: #f0f0f0; margin: 0; }');
    fs.writeFileSync(path.join(scDir, 'src', 'main.js'), ['import "@/theme.css";', 'export const appTitle = "ViteAssetTest";'].join(String.fromCharCode(10)));
    fs.writeFileSync(path.join(scDir, 'index.html'), '<html><head><link rel="icon" href="/robots.txt"></head><body><script type="module" src="/src/main.js"></script></body></html>');

    const outDir = path.join(scDir, 'dist');
    await build({
      root: scDir,
      base: '/app-base/',
      logLevel: 'silent',
      resolve: {
        alias: {
          '@': path.join(scDir, 'src')
        }
      },
      build: { outDir, emptyOutDir: true }
    });

    const distFiles = getAllFiles(outDir);
    const aliasResolved = distFiles.some(f => f.endsWith('.js'));
    const builtHtml = fs.existsSync(path.join(outDir, 'index.html')) ? fs.readFileSync(path.join(outDir, 'index.html'), 'utf-8') : '';
    const publicCopied = fs.existsSync(path.join(outDir, 'robots.txt')) &&
      fs.readFileSync(path.join(outDir, 'robots.txt'), 'utf-8').includes('Disallow: /') &&
      builtHtml.includes('/app-base/robots.txt');
    const cssProcessed = distFiles.some(f => f.startsWith('assets') && f.endsWith('.css'));

    const assertions = [
      { name: 'alias_resolved_in_bundle', passed: aliasResolved },
      { name: 'public_asset_copied_verbatim', passed: publicCopied },
      { name: 'css_processed_and_hashed', passed: cssProcessed }
    ];

    results.push({
      scenario_id: 'VITE03',
      name: 'asset_public_css_alias',
      status: assertions.every(a => a.passed) ? 'passed' : 'failed',
      duration_ms: Date.now() - start,
      assertions,
      error: null
    });
  }

  // Scenario VITE04: Plugin Ordering and Apply
  if (targetScenarios.includes('VITE04')) {
    const start = Date.now();
    const scDir = prepareScenarioDir('VITE04');
    fs.mkdirSync(path.join(scDir, 'src'), { recursive: true });

    const pluginTrace = [];
    const pluginPre = {
      name: 'plugin-pre',
      enforce: 'pre',
      buildStart() { pluginTrace.push('pre'); }
    };
    const pluginPost = {
      name: 'plugin-post',
      enforce: 'post',
      buildStart() { pluginTrace.push('post'); }
    };
    const pluginServe = {
      name: 'plugin-serve-only',
      apply: 'serve',
      buildStart() { pluginTrace.push('serve'); }
    };
    const pluginBuild = {
      name: 'plugin-build-only',
      apply: 'build',
      buildStart() { pluginTrace.push('build'); }
    };
    const virtualModulePlugin = {
      name: 'virtual-module',
      resolveId(id) {
        if (id === 'virtual:calc') return '\0virtual:calc';
      },
      load(id) {
        if (id === '\0virtual:calc') return 'export const magicNumber = 420;';
      }
    };

    fs.writeFileSync(path.join(scDir, 'index.html'), '<html><body><script type="module" src="/src/main.js"></script></body></html>');
    fs.writeFileSync(path.join(scDir, 'src', 'main.js'), ['import { magicNumber } from "virtual:calc";', 'console.log(magicNumber);'].join(String.fromCharCode(10)));

    const outDir = path.join(scDir, 'dist');
    await build({
      root: scDir,
      logLevel: 'silent',
      plugins: [pluginPost, pluginPre, pluginServe, pluginBuild, virtualModulePlugin],
      build: { outDir, emptyOutDir: true }
    });

    const preIndex = pluginTrace.indexOf('pre');
    const postIndex = pluginTrace.indexOf('post');
    const preBeforePost = preIndex !== -1 && postIndex !== -1 && preIndex < postIndex;
    const buildApplied = pluginTrace.includes('build');
    const serveSkipped = !pluginTrace.includes('serve');

    const distFiles = getAllFiles(outDir);
    const jsFiles = distFiles.filter(f => f.endsWith('.js'));
    let virtualResolved = false;
    for (const f of jsFiles) {
      if (fs.readFileSync(path.join(outDir, f), 'utf-8').includes('420')) {
        virtualResolved = true;
        break;
      }
    }

    const assertions = [
      { name: 'pre_plugin_ordered_before_post', passed: preBeforePost },
      { name: 'build_plugin_applied', passed: buildApplied },
      { name: 'serve_plugin_skipped_in_build', passed: serveSkipped },
      { name: 'virtual_module_resolved', passed: virtualResolved }
    ];

    results.push({
      scenario_id: 'VITE04',
      name: 'plugin_ordering_and_apply',
      status: assertions.every(a => a.passed) ? 'passed' : 'failed',
      duration_ms: Date.now() - start,
      assertions,
      error: null
    });
  }

  // Scenario VITE05: Loopback Dev Server & FS Restrictions
  if (targetScenarios.includes('VITE05')) {
    const start = Date.now();
    const scDir = prepareScenarioDir('VITE05');
    const outsideDir = path.join(runDir, 'outside-sc05');
    fs.mkdirSync(outsideDir, { recursive: true });

    fs.writeFileSync(path.join(scDir, 'index.html'), '<h1>VITE05 OK</h1>');
    fs.writeFileSync(path.join(scDir, 'secret.env'), 'SECRET_DATA');
    fs.writeFileSync(path.join(outsideDir, 'external.txt'), 'EXTERNAL_DATA');

    let server;
    let loopbackBound = false;
    let allowedOk = false;
    let denied403 = false;
    let traversal403 = false;
    let serverClosedCleanly = false;

    try {
      server = await createServer({
        root: scDir,
        logLevel: 'silent',
        server: {
          host: '127.0.0.1',
          port: 0,
          fs: {
            strict: true,
            allow: [scDir],
            deny: [path.join(scDir, 'secret.env')]
          }
        }
      });

      await server.listen();
      const addr = server.httpServer.address();
      const port = addr.port;
      loopbackBound = addr.address === '127.0.0.1';

      const resOk = await httpGet('127.0.0.1', port, '/index.html');
      allowedOk = resOk.status === 200 && resOk.data.includes('VITE05 OK');

      const resDenied = await httpGet('127.0.0.1', port, '/secret.env');
      denied403 = resDenied.status === 403;

      const resTraversal = await httpGet('127.0.0.1', port, '/@fs/' + outsideDir + '/external.txt');
      traversal403 = resTraversal.status === 403;
    } finally {
      if (server) {
        try {
          await server.close();
          serverClosedCleanly = true;
        } catch {}
      }
    }

    const assertions = [
      { name: 'loopback_server_bound', passed: loopbackBound },
      { name: 'allowed_file_200_ok', passed: allowedOk },
      { name: 'denied_file_403_forbidden', passed: denied403 },
      { name: 'outside_traversal_403_forbidden', passed: traversal403 },
      { name: 'server_closed_cleanly', passed: serverClosedCleanly }
    ];

    results.push({
      scenario_id: 'VITE05',
      name: 'loopback_dev_fs_restrictions',
      status: assertions.every(a => a.passed) ? 'passed' : 'failed',
      duration_ms: Date.now() - start,
      assertions,
      error: null
    });
  }

  // Scenario VITE06: HMR & Module Graph Invalidation
  if (targetScenarios.includes('VITE06')) {
    const start = Date.now();
    const scDir = prepareScenarioDir('VITE06');
    fs.mkdirSync(path.join(scDir, 'src'), { recursive: true });
    fs.writeFileSync(path.join(scDir, 'index.html'), '<html><body><script type="module" src="/src/main.js"></script></body></html>');
    fs.writeFileSync(path.join(scDir, 'src', 'main.js'), 'export const count = 1;');

    let server;
    let entryResolved = false;
    let invalidated = false;
    let serverClosedCleanly = false;

    try {
      server = await createServer({
        root: scDir,
        logLevel: 'silent',
        server: {
          host: '127.0.0.1',
          port: 0
        }
      });

      await server.listen();
      const port = server.httpServer.address().port;

      const res1 = await httpGet('127.0.0.1', port, '/src/main.js');
      const mod = server.moduleGraph.urlToModuleMap.get('/src/main.js') ||
        server.moduleGraph.getModuleById(path.join(scDir, 'src', 'main.js'));
      
      entryResolved = mod !== undefined && mod.transformResult !== null;

      if (mod) {
        server.moduleGraph.invalidateModule(mod);
        invalidated = mod.transformResult === null;
      }
    } finally {
      if (server) {
        try {
          await server.close();
          serverClosedCleanly = true;
        } catch {}
      }
    }

    const assertions = [
      { name: 'module_graph_entry_resolved', passed: entryResolved },
      { name: 'module_invalidation_detected', passed: invalidated },
      { name: 'server_closed_cleanly', passed: serverClosedCleanly }
    ];

    results.push({
      scenario_id: 'VITE06',
      name: 'hmr_module_invalidation',
      status: assertions.every(a => a.passed) ? 'passed' : 'failed',
      duration_ms: Date.now() - start,
      assertions,
      error: null
    });
  }

  // Scenario VITE07: Production Build & Manifest
  if (targetScenarios.includes('VITE07')) {
    const start = Date.now();
    const scDir = prepareScenarioDir('VITE07');
    fs.mkdirSync(path.join(scDir, 'src'), { recursive: true });
    fs.writeFileSync(path.join(scDir, 'src', 'style.css'), 'h1 { color: blue; }');
    fs.writeFileSync(path.join(scDir, 'src', 'main.js'), ['import "./style.css";', 'console.log("manifest test");'].join(String.fromCharCode(10)));
    fs.writeFileSync(path.join(scDir, 'index.html'), '<html><body><script type="module" src="/src/main.js"></script></body></html>');

    const outDir = path.join(scDir, 'dist');
    await build({
      root: scDir,
      logLevel: 'silent',
      build: {
        outDir,
        emptyOutDir: true,
        manifest: true
      }
    });

    const manifestPath = path.join(outDir, '.vite', 'manifest.json');
    const manifestExists = fs.existsSync(manifestPath);
    let entryMapped = false;
    let cssTracked = false;

    if (manifestExists) {
      const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
      for (const [key, entry] of Object.entries(manifest)) {
        if (entry.isEntry && entry.file && entry.file.startsWith('assets/')) {
          entryMapped = true;
          if (Array.isArray(entry.css) && entry.css.length > 0) {
            cssTracked = true;
          }
        }
      }
    }

    const assertions = [
      { name: 'manifest_json_generated', passed: manifestExists },
      { name: 'entry_mapped_to_hashed_chunk', passed: entryMapped },
      { name: 'css_assets_tracked_in_manifest', passed: cssTracked }
    ];

    results.push({
      scenario_id: 'VITE07',
      name: 'production_manifest',
      status: assertions.every(a => a.passed) ? 'passed' : 'failed',
      duration_ms: Date.now() - start,
      assertions,
      error: null
    });
  }

  // Scenario VITE08: Dynamic Import & Library Mode
  if (targetScenarios.includes('VITE08')) {
    const start = Date.now();
    const scDir = prepareScenarioDir('VITE08');
    fs.mkdirSync(path.join(scDir, 'src'), { recursive: true });

    // 1. Dynamic Import
    fs.writeFileSync(path.join(scDir, 'src', 'dynamic.js'), 'export function dynamicFeature() { return "loaded"; }');
    fs.writeFileSync(path.join(scDir, 'src', 'main.js'), 'import("./dynamic.js").then(m => console.log(m.dynamicFeature()));');
    fs.writeFileSync(path.join(scDir, 'index.html'), '<html><body><script type="module" src="/src/main.js"></script></body></html>');

    const outDirApp = path.join(scDir, 'dist-app');
    await build({
      root: scDir,
      logLevel: 'silent',
      build: { outDir: outDirApp, emptyOutDir: true }
    });

    const appFiles = getAllFiles(outDirApp);
    const jsChunks = appFiles.filter(f => f.startsWith('assets') && f.endsWith('.js'));
    const dynamicSplit = jsChunks.length >= 2;

    // 2. Library Mode
    fs.writeFileSync(path.join(scDir, 'src', 'lib.js'), 'export function add(a, b) { return a + b; }');
    const outDirLib = path.join(scDir, 'dist-lib');
    await build({
      root: scDir,
      logLevel: 'silent',
      build: {
        outDir: outDirLib,
        emptyOutDir: true,
        lib: {
          entry: path.join(scDir, 'src', 'lib.js'),
          name: 'MyApgLib',
          fileName: (format) => 'my-lib.' + format + '.js',
          formats: ['es', 'cjs']
        }
      }
    });

    const libFiles = getAllFiles(outDirLib);
    const esmGenerated = libFiles.includes('my-lib.es.js');
    const cjsGenerated = libFiles.includes('my-lib.cjs.js');

    const assertions = [
      { name: 'dynamic_import_chunk_split', passed: dynamicSplit },
      { name: 'lib_esm_format_generated', passed: esmGenerated },
      { name: 'lib_cjs_format_generated', passed: cjsGenerated }
    ];

    results.push({
      scenario_id: 'VITE08',
      name: 'dynamic_import_and_library_mode',
      status: assertions.every(a => a.passed) ? 'passed' : 'failed',
      duration_ms: Date.now() - start,
      assertions,
      error: null
    });
  }

  // Scenario VITE09: Sourcemap Toggle
  if (targetScenarios.includes('VITE09')) {
    const start = Date.now();
    const scDir = prepareScenarioDir('VITE09');
    fs.mkdirSync(path.join(scDir, 'src'), { recursive: true });
    fs.writeFileSync(path.join(scDir, 'src', 'main.js'), 'console.log("calculating", 42);');
    fs.writeFileSync(path.join(scDir, 'index.html'), '<html><body><script type="module" src="/src/main.js"></script></body></html>');

    // Build with sourcemap: true
    const outDirWithMap = path.join(scDir, 'dist-with-map');
    await build({
      root: scDir,
      logLevel: 'silent',
      build: {
        outDir: outDirWithMap,
        emptyOutDir: true,
        sourcemap: true
      }
    });
    const withMapFiles = getAllFiles(outDirWithMap);
    const mapGenerated = withMapFiles.some(f => f.endsWith('.js.map'));

    // Build with sourcemap: false
    const outDirNoMap = path.join(scDir, 'dist-no-map');
    await build({
      root: scDir,
      logLevel: 'silent',
      build: {
        outDir: outDirNoMap,
        emptyOutDir: true,
        sourcemap: false
      }
    });
    const noMapFiles = getAllFiles(outDirNoMap);
    const mapOmitted = !noMapFiles.some(f => f.endsWith('.map'));

    const assertions = [
      { name: 'sourcemap_enabled_generates_map', passed: mapGenerated },
      { name: 'sourcemap_disabled_omits_map', passed: mapOmitted }
    ];

    results.push({
      scenario_id: 'VITE09',
      name: 'sourcemap_toggle',
      status: assertions.every(a => a.passed) ? 'passed' : 'failed',
      duration_ms: Date.now() - start,
      assertions,
      error: null
    });
  }

  // Scenario VITE10: Preview Local-Only Server
  if (targetScenarios.includes('VITE10')) {
    const start = Date.now();
    const scDir = prepareScenarioDir('VITE10');
    fs.writeFileSync(path.join(scDir, 'index.html'), '<!DOCTYPE html><html><body><h1>Preview App</h1></body></html>');

    const outDir = path.join(scDir, 'dist');
    await build({
      root: scDir,
      logLevel: 'silent',
      build: { outDir, emptyOutDir: true }
    });

    let previewServer;
    let loopbackBound = false;
    let servesOk = false;
    let previewClosedCleanly = false;

    try {
      previewServer = await preview({
        root: scDir,
        logLevel: 'silent',
        preview: {
          host: '127.0.0.1',
          port: 0
        },
        build: { outDir }
      });

      const addr = previewServer.httpServer.address();
      loopbackBound = addr.address === '127.0.0.1';
      const res = await httpGet('127.0.0.1', addr.port, '/');
      servesOk = res.status === 200 && res.data.includes('Preview App');
    } finally {
      if (previewServer) {
        try {
          await previewServer.close();
          previewClosedCleanly = true;
        } catch {}
      }
    }

    const assertions = [
      { name: 'preview_loopback_bound', passed: loopbackBound },
      { name: 'preview_serves_build_200_ok', passed: servesOk },
      { name: 'preview_closed_cleanly', passed: previewClosedCleanly }
    ];

    results.push({
      scenario_id: 'VITE10',
      name: 'preview_local_only',
      status: assertions.every(a => a.passed) ? 'passed' : 'failed',
      duration_ms: Date.now() - start,
      assertions,
      error: null
    });
  }

  // Scenario VITE11: Two Builds Determinism
  if (targetScenarios.includes('VITE11')) {
    const start = Date.now();
    const scDir = prepareScenarioDir('VITE11');
    fs.mkdirSync(path.join(scDir, 'src'), { recursive: true });
    fs.mkdirSync(path.join(scDir, 'public'), { recursive: true });

    fs.writeFileSync(path.join(scDir, 'public', 'static.txt'), 'STATIC ASSET');
    fs.writeFileSync(path.join(scDir, 'src', 'main.js'), 'export const value = 12345678;');
    fs.writeFileSync(path.join(scDir, 'index.html'), '<html><body><script type="module" src="/src/main.js"></script></body></html>');

    const outDir1 = path.join(scDir, 'dist-1');
    const outDir2 = path.join(scDir, 'dist-2');

    await build({
      root: scDir,
      logLevel: 'silent',
      build: { outDir: outDir1, emptyOutDir: true, manifest: true }
    });

    await build({
      root: scDir,
      logLevel: 'silent',
      build: { outDir: outDir2, emptyOutDir: true, manifest: true }
    });

    const files1 = getAllFiles(outDir1);
    const files2 = getAllFiles(outDir2);
    const manifestIdentical = JSON.stringify(files1) === JSON.stringify(files2);

    let sha256Identical = manifestIdentical;
    if (manifestIdentical) {
      for (const f of files1) {
        const hash1 = sha256File(path.join(outDir1, f));
        const hash2 = sha256File(path.join(outDir2, f));
        if (hash1 !== hash2) {
          sha256Identical = false;
          break;
        }
      }
    }

    const assertions = [
      { name: 'two_builds_file_manifest_identical', passed: manifestIdentical },
      { name: 'two_builds_sha256_identical', passed: sha256Identical }
    ];

    results.push({
      scenario_id: 'VITE11',
      name: 'two_builds_determinism',
      status: assertions.every(a => a.passed) ? 'passed' : 'failed',
      duration_ms: Date.now() - start,
      assertions,
      error: null
    });
  }

  // Scenario VITE12: Misconfiguration Negatives
  if (targetScenarios.includes('VITE12')) {
    const start = Date.now();
    const scDir = prepareScenarioDir('VITE12');

    let missingLibraryEntryRefused = false;
    try {
      await build({
        root: scDir,
        logLevel: 'silent',
        build: {
          lib: {
            entry: path.join(scDir, 'nonexistent-entry-file-404.js'),
            name: 'BrokenLib'
          }
        }
      });
    } catch (err) {
      const code = err?.errors?.[0]?.code || err?.code;
      const msg = err?.errors?.[0]?.message || err?.message || '';
      missingLibraryEntryRefused = (
        (err instanceof Error || err?.name === 'Error') &&
        code === 'UNRESOLVED_ENTRY' &&
        msg.includes('Cannot resolve entry module') &&
        msg.includes('nonexistent-entry-file-404.js')
      );
    }

    let misconfiguredInputRefused = false;
    try {
      await build({
        root: path.join(scDir, 'nonexistent-root-dir'),
        logLevel: 'silent'
      });
    } catch (err) {
      const code = err?.errors?.[0]?.code || err?.code;
      const msg = err?.errors?.[0]?.message || err?.message || '';
      misconfiguredInputRefused = (
        (err instanceof Error || err?.name === 'Error') &&
        code === 'UNRESOLVED_ENTRY' &&
        msg.includes('Cannot resolve entry module') &&
        msg.includes('nonexistent-root-dir')
      );
    }

    const assertions = [
      { name: 'missing_library_entry_refused', passed: missingLibraryEntryRefused },
      { name: 'misconfigured_input_refused', passed: misconfiguredInputRefused }
    ];

    results.push({
      scenario_id: 'VITE12',
      name: 'misconfiguration_negatives',
      status: assertions.every(a => a.passed) ? 'passed' : 'failed',
      duration_ms: Date.now() - start,
      assertions,
      error: null
    });
  }

} finally {
  fs.rmSync(runDir, { recursive: true, force: true });
}

const passedCount = results.filter(r => r.status === 'passed').length;
const failedCount = results.filter(r => r.status === 'failed').length;

const receipt = {
  schema_version: '1.0.0',
  toolchain: {
    vite_version: vite.version,
    node_version: process.version,
    node_identity: process.version + '|' + process.platform + '/' + process.arch + '|' + process.versions.v8 + '|' + process.versions.uv
  },
  summary: {
    total: results.length,
    passed: passedCount,
    failed: failedCount,
    skipped: 0
  },
  scenarios: results,
  retained_on_disk: false
};

const receiptJson = JSON.stringify(receipt, null, 2);
if (outputFile) {
  fs.mkdirSync(path.dirname(outputFile), { recursive: true });
  fs.writeFileSync(outputFile, receiptJson, 'utf-8');
}

console.log(receiptJson);
process.exit(failedCount === 0 ? 0 : 1);
