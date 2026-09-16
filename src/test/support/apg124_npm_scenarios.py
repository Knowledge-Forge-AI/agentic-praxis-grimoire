"""APG124 synthetic npm scenario bodies; runtime custody stays in apg124_npm."""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil

def scenario_npm01(config, fixtures_dir: Path, sc_scratch: Path, cache_dir: Path, run_npm_subprocess):
    """Execute NPM01 predicates against the selected npm CLI."""
    assertions = []
    clean_src = fixtures_dir / "projects" / "clean-ci"
    work_dir = sc_scratch / "app"
    shutil.copytree(clean_src, work_dir)
    dep_dir = sc_scratch / "dep-a"
    shutil.copytree(fixtures_dir / "packages" / "dep-a", dep_dir)

    lock_before = (work_dir / "package-lock.json").read_text(encoding="utf-8")
    res = run_npm_subprocess(config, ["ci", "--ignore-scripts", "--no-audit", "--no-fund"], work_dir, cache_dir)

    exit_zero = (res.returncode == 0)
    dep_installed = (work_dir / "node_modules" / "dep-a").exists()
    hidden_lock = (work_dir / "node_modules" / ".package-lock.json").exists()
    lock_after = (work_dir / "package-lock.json").read_text(encoding="utf-8")
    lock_unmodified = (lock_before == lock_after)

    assertions.append({"name": "exit_code_zero", "passed": exit_zero})
    assertions.append({"name": "dependency_installed", "passed": dep_installed})
    assertions.append({"name": "hidden_lockfile_created", "passed": hidden_lock})
    assertions.append({"name": "lockfile_unmodified", "passed": lock_unmodified})

    return assertions


def scenario_npm02(config, fixtures_dir: Path, sc_scratch: Path, cache_dir: Path, run_npm_subprocess):
    """Execute NPM02 predicates against the selected npm CLI."""
    assertions = []
    stale_src = fixtures_dir / "projects" / "stale-lock"
    work_dir = sc_scratch / "app"
    shutil.copytree(stale_src, work_dir)
    shutil.copytree(fixtures_dir / "packages" / "dep-a", sc_scratch / "dep-a")
    shutil.copytree(fixtures_dir / "packages" / "dep-b", sc_scratch / "dep-b")

    res = run_npm_subprocess(config, ["ci", "--ignore-scripts", "--no-audit", "--no-fund"], work_dir, cache_dir)

    exit_nonzero = (res.returncode != 0)
    sync_error = ("in sync" in res.stderr.lower() or "eusage" in res.stderr.lower())
    missing_dep = ("apgr-apg124-fixture-dep-b" in res.stderr)

    assertions.append({"name": "exit_code_nonzero", "passed": exit_nonzero})
    assertions.append({"name": "sync_error_reported", "passed": sync_error})
    assertions.append({"name": "missing_dep_reported", "passed": missing_dep})

    return assertions


def scenario_npm03(config, fixtures_dir: Path, sc_scratch: Path, cache_dir: Path, run_npm_subprocess):
    """Execute NPM03 predicates against the selected npm CLI."""
    assertions = []
    update_src = fixtures_dir / "projects" / "install-update"
    work_dir = sc_scratch / "app"
    shutil.copytree(update_src, work_dir)
    shutil.copytree(fixtures_dir / "packages" / "dep-a", sc_scratch / "dep-a")
    shutil.copytree(fixtures_dir / "packages" / "dep-b", sc_scratch / "dep-b")

    res = run_npm_subprocess(config, ["install", "--ignore-scripts", "--no-audit", "--no-fund"], work_dir, cache_dir)

    exit_zero = (res.returncode == 0)
    dep_installed = (work_dir / "node_modules" / "apgr-apg124-fixture-dep-b").exists()
    lock_data = json.loads((work_dir / "package-lock.json").read_text(encoding="utf-8"))
    packages = lock_data.get("packages", {})
    lock_updated = any("apgr-apg124-fixture-dep-b" in k for k in packages.keys())

    assertions.append({"name": "exit_code_zero", "passed": exit_zero})
    assertions.append({"name": "dependency_installed", "passed": dep_installed})
    assertions.append({"name": "lockfile_updated_with_new_dep", "passed": lock_updated})

    return assertions


def scenario_npm04(config, fixtures_dir: Path, sc_scratch: Path, cache_dir: Path, run_npm_subprocess):
    """Execute NPM04 predicates against the selected npm CLI."""
    assertions = []
    ws_src = fixtures_dir / "projects" / "workspaces"
    work_dir = sc_scratch / "monorepo"
    shutil.copytree(ws_src, work_dir)

    res_inst = run_npm_subprocess(config, ["install", "--ignore-scripts", "--no-audit", "--no-fund"], work_dir, cache_dir)
    exit_zero = (res_inst.returncode == 0)
    symlink_created = (work_dir / "node_modules" / "lib-pkg").exists()

    res_run = run_npm_subprocess(config, ["run", "greet", "--workspace=lib-pkg"], work_dir, cache_dir)
    script_output = "GREETINGS_FROM_LIB_PKG" in res_run.stdout

    assertions.append({"name": "exit_code_zero", "passed": exit_zero})
    assertions.append({"name": "workspace_symlink_created", "passed": symlink_created})
    assertions.append({"name": "workspace_script_output_verified", "passed": script_output})

    return assertions


def scenario_npm05(config, fixtures_dir: Path, sc_scratch: Path, cache_dir: Path, run_npm_subprocess):
    """Execute NPM05 predicates against the selected npm CLI."""
    assertions = []
    work_dir = sc_scratch / "app"
    work_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(fixtures_dir / "packages" / "host-pkg-v1", sc_scratch / "host-pkg-v1")
    shutil.copytree(fixtures_dir / "packages" / "plugin-pkg", sc_scratch / "plugin-pkg")

    (work_dir / "package.json").write_text(json.dumps({
        "name": "peer-success-app",
        "version": "1.0.0",
        "dependencies": {
            "host-pkg": "file:../host-pkg-v1",
            "plugin-pkg": "file:../plugin-pkg",
        }
    }, indent=2) + "\n", encoding="utf-8")

    res = run_npm_subprocess(config, ["install", "--install-links", "--ignore-scripts", "--no-audit", "--no-fund"], work_dir, cache_dir)
    exit_zero = (res.returncode == 0)
    installed = (work_dir / "node_modules" / "host-pkg").exists() and (work_dir / "node_modules" / "plugin-pkg").exists()

    assertions.append({"name": "exit_code_zero", "passed": exit_zero})
    assertions.append({"name": "peer_and_host_installed", "passed": installed})

    return assertions


def scenario_npm06(config, fixtures_dir: Path, sc_scratch: Path, cache_dir: Path, run_npm_subprocess):
    """Execute NPM06 predicates against the selected npm CLI."""
    assertions = []
    work_dir = sc_scratch / "app"
    work_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(fixtures_dir / "packages" / "host-pkg-v2", sc_scratch / "host-pkg-v2")
    shutil.copytree(fixtures_dir / "packages" / "plugin-pkg", sc_scratch / "plugin-pkg")

    (work_dir / "package.json").write_text(json.dumps({
        "name": "peer-conflict-app",
        "version": "1.0.0",
        "dependencies": {
            "host-pkg": "file:../host-pkg-v2",
            "plugin-pkg": "file:../plugin-pkg",
        }
    }, indent=2) + "\n", encoding="utf-8")

    res = run_npm_subprocess(config, ["install", "--install-links", "--ignore-scripts", "--no-audit", "--no-fund"], work_dir, cache_dir)
    exit_nonzero = (res.returncode != 0)
    eresolve = "eresolve" in res.stderr.lower() or "unable to resolve dependency tree" in res.stderr.lower()

    assertions.append({"name": "exit_code_nonzero", "passed": exit_nonzero})
    assertions.append({"name": "eresolve_conflict_reported", "passed": eresolve})

    return assertions


def scenario_npm07(config, fixtures_dir: Path, sc_scratch: Path, cache_dir: Path, run_npm_subprocess):
    """Execute NPM07 predicates against the selected npm CLI."""
    assertions = []
    work_dir = sc_scratch / "app"
    work_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(fixtures_dir / "packages" / "host-pkg-v2", sc_scratch / "host-pkg-v2")
    shutil.copytree(fixtures_dir / "packages" / "plugin-pkg", sc_scratch / "plugin-pkg")

    (work_dir / "package.json").write_text(json.dumps({
        "name": "overrides-app",
        "version": "1.0.0",
        "dependencies": {
            "host-pkg": "file:../host-pkg-v2",
            "plugin-pkg": "file:../plugin-pkg",
        },
        "overrides": {
            "plugin-pkg": {
                "host-pkg": "file:../host-pkg-v2"
            }
        }
    }, indent=2) + "\n", encoding="utf-8")

    res = run_npm_subprocess(config, ["install", "--install-links", "--ignore-scripts", "--no-audit", "--no-fund"], work_dir, cache_dir)
    exit_zero = (res.returncode == 0)
    applied = (work_dir / "node_modules" / "host-pkg").exists() and (work_dir / "node_modules" / "plugin-pkg").exists()

    # Assert installed overridden version and exported content
    host_pkg_json = work_dir / "node_modules" / "host-pkg" / "package.json"
    version_verified = False
    if host_pkg_json.is_file():
        try:
            pj = json.loads(host_pkg_json.read_text(encoding="utf-8"))
            version_verified = (pj.get("version") == "2.0.0")
        except Exception:
            pass

    host_index_js = work_dir / "node_modules" / "host-pkg" / "index.js"
    content_verified = False
    if host_index_js.is_file():
        c_text = host_index_js.read_text(encoding="utf-8")
        content_verified = ('version: "2.0.0"' in c_text or "'version': '2.0.0'" in c_text or '"2.0.0"' in c_text)

    assertions.append({"name": "exit_code_zero", "passed": exit_zero})
    assertions.append({"name": "override_applied_successfully", "passed": applied})
    assertions.append({"name": "overridden_version_verified", "passed": version_verified})
    assertions.append({"name": "overridden_content_verified", "passed": content_verified})

    return assertions


def scenario_npm08(config, fixtures_dir: Path, sc_scratch: Path, cache_dir: Path, run_npm_subprocess):
    """Execute NPM08 predicates against the selected npm CLI."""
    assertions = []
    work_dir = sc_scratch / "app"
    work_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(fixtures_dir / "packages" / "opt-supported", sc_scratch / "opt-supported")
    shutil.copytree(fixtures_dir / "packages" / "opt-unsupported", sc_scratch / "opt-unsupported")

    (work_dir / "package.json").write_text(json.dumps({
        "name": "opt-app",
        "version": "1.0.0",
        "optionalDependencies": {
            "opt-supported": "file:../opt-supported",
            "opt-unsupported": "file:../opt-unsupported",
        }
    }, indent=2) + "\n", encoding="utf-8")

    res = run_npm_subprocess(config, ["install", "--install-links", "--ignore-scripts", "--no-audit", "--no-fund"], work_dir, cache_dir)
    exit_zero = (res.returncode == 0)
    supp_installed = (work_dir / "node_modules" / "opt-supported").exists()
    unsupp_skipped = not (work_dir / "node_modules" / "opt-unsupported").exists()

    assertions.append({"name": "exit_code_zero", "passed": exit_zero})
    assertions.append({"name": "supported_optional_installed", "passed": supp_installed})
    assertions.append({"name": "unsupported_optional_skipped", "passed": unsupp_skipped})

    return assertions


def scenario_npm09(config, fixtures_dir: Path, sc_scratch: Path, cache_dir: Path, run_npm_subprocess):
    """Execute NPM09 predicates against the selected npm CLI."""
    assertions = []
    shutil.copytree(fixtures_dir / "packages" / "dep-lifecycle", sc_scratch / "dep-lifecycle")

    # Step 1: Positive installation lifecycle execution
    pos_dir = sc_scratch / "app-pos"
    shutil.copytree(fixtures_dir / "projects" / "lifecycle", pos_dir)
    # npm 12 approval matches the resolved local source, not its package name.
    manifest = json.loads((pos_dir / "package.json").read_text())
    manifest["allowScripts"] = {f"file:{sc_scratch / 'dep-lifecycle'}": True}
    (pos_dir / "package.json").write_text(json.dumps(manifest))
    res_pos = run_npm_subprocess(
        config,
        ["install", "--install-links", "--no-audit", "--no-fund"],
        pos_dir,
        cache_dir
    )
    pos_exit = (res_pos.returncode == 0)
    life_log = pos_dir / "lifecycle-order.txt"
    root_lifecycle_executed = (
        life_log.is_file()
        and life_log.read_text(encoding="utf-8").strip() == "ROOT_PREINSTALL\nROOT_POSTINSTALL"
    )
    dep_witness = pos_dir / "node_modules" / "dep-lifecycle" / "dep-witness.txt"
    dep_executed = (
        dep_witness.is_file()
        and dep_witness.read_text(encoding="utf-8").strip() == "DEP_LIFECYCLE_EXECUTED"
    )

    # Step 2: Suppression under --ignore-scripts
    sup_dir = sc_scratch / "app-sup"
    shutil.copytree(fixtures_dir / "projects" / "lifecycle", sup_dir)
    (sup_dir / "package.json").write_text(json.dumps(manifest))
    res_sup = run_npm_subprocess(
        config,
        ["install", "--install-links", "--ignore-scripts", "--no-audit", "--no-fund"],
        sup_dir,
        cache_dir
    )
    sup_exit = (res_sup.returncode == 0)
    sup_life_log = sup_dir / "lifecycle-order.txt"
    sup_dep_witness = sup_dir / "node_modules" / "dep-lifecycle" / "dep-witness.txt"
    lifecycle_suppressed = sup_exit and (not sup_life_log.exists()) and (not sup_dep_witness.exists())

    # Step 3: Explicit npm run normal execution verifies pre/post hook ordering
    res_run = run_npm_subprocess(config, ["run", "build"], pos_dir, cache_dir)
    run_log = pos_dir / "run-order.txt"
    pre_post_order_ok = (
        res_run.returncode == 0
        and run_log.is_file()
        and run_log.read_text(encoding="utf-8").strip() == "PREBUILD\nBUILD\nPOSTBUILD"
    )

    # Step 4: Explicit npm run under ignore-scripts suppresses pre/post hooks while executing target
    res_run_sup = run_npm_subprocess(
        config,
        ["run", "build", "--ignore-scripts"],
        sup_dir,
        cache_dir,
        extra_env={"npm_config_ignore_scripts": "true"}
    )
    sup_run_log = sup_dir / "run-order.txt"
    hooks_suppressed_ok = (
        res_run_sup.returncode == 0
        and sup_run_log.is_file()
        and sup_run_log.read_text(encoding="utf-8").strip() == "BUILD"
    )

    assertions.append({"name": "install_positive_lifecycle_executed", "passed": pos_exit and root_lifecycle_executed})
    assertions.append({"name": "dependency_lifecycle_executed", "passed": pos_exit and dep_executed})
    assertions.append({"name": "install_lifecycle_suppressed", "passed": lifecycle_suppressed})
    assertions.append({"name": "run_pre_post_order_verified", "passed": pre_post_order_ok})
    assertions.append({"name": "run_ignore_scripts_suppressed_hooks", "passed": hooks_suppressed_ok})

    return assertions


def scenario_npm10(config, fixtures_dir: Path, sc_scratch: Path, cache_dir: Path, run_npm_subprocess):
    """Execute NPM10 predicates against the selected npm CLI."""
    assertions = []
    pack_dir = sc_scratch / "packable"
    shutil.copytree(fixtures_dir / "packages" / "packable-pkg", pack_dir)

    res_pack = run_npm_subprocess(config, ["pack", "--json"], pack_dir, cache_dir)
    pack_exit = (res_pack.returncode == 0)

    pack_obj = json.loads(res_pack.stdout)
    pkg_data = pack_obj.get("packable-pkg") or (pack_obj[0] if isinstance(pack_obj, list) else {})
    tarball_name = pkg_data.get("filename", "packable-pkg-1.0.0.tgz")
    files_archived = [f["path"] for f in pkg_data.get("files", [])]

    files_ok = ("index.js" in files_archived and "bin/cli.js" in files_archived and "package.json" in files_archived)
    unlisted_excluded = ("ignored.txt" not in files_archived)

    # Consumer project installs resulting tarball
    consumer_dir = sc_scratch / "consumer"
    consumer_dir.mkdir(parents=True, exist_ok=True)
    (consumer_dir / "package.json").write_text(json.dumps({
        "name": "consumer-app",
        "version": "1.0.0"
    }, indent=2) + "\n", encoding="utf-8")

    tarball_path = pack_dir / tarball_name
    res_inst = run_npm_subprocess(config, ["install", "--ignore-scripts", "--no-audit", "--no-fund", str(tarball_path)], consumer_dir, cache_dir)
    inst_exit = (res_inst.returncode == 0)
    consumer_installed = (consumer_dir / "node_modules" / "packable-pkg" / "index.js").exists() and (consumer_dir / "node_modules" / ".bin" / "packable-cli").exists()

    assertions.append({"name": "pack_exit_code_zero", "passed": pack_exit})
    assertions.append({"name": "pack_files_allowlist_verified", "passed": files_ok})
    assertions.append({"name": "unlisted_files_excluded", "passed": unlisted_excluded})
    assertions.append({"name": "tarball_install_exit_code_zero", "passed": inst_exit})
    assertions.append({"name": "consumer_bin_and_module_installed", "passed": consumer_installed})

    return assertions


def scenario_npm11(config, fixtures_dir: Path, sc_scratch: Path, cache_dir: Path, run_npm_subprocess):
    """Execute NPM11 predicates against the selected npm CLI."""
    assertions = []
    global_rc = sc_scratch / "global.npmrc"
    user_rc = sc_scratch / "user.npmrc"
    empty_rc = sc_scratch / "empty.npmrc"
    empty_rc.write_text("", encoding="utf-8")

    global_rc.write_text("registry=https://global.registry.invalid/\n", encoding="utf-8")
    user_rc.write_text("registry=https://user.registry.invalid/\n", encoding="utf-8")

    # Project directory with project .npmrc
    work_dir = sc_scratch / "project-app"
    work_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / ".npmrc").write_text("registry=https://project.registry.invalid/\n", encoding="utf-8")

    # Clean directory without project .npmrc for testing global and user configs
    plain_dir = sc_scratch / "plain-app"
    plain_dir.mkdir(parents=True, exist_ok=True)

    # 1. Global only: plain dir, global config, empty user config
    r1 = run_npm_subprocess(
        config,
        ["config", "get", "registry"],
        plain_dir,
        cache_dir,
        extra_env={
            "npm_config_globalconfig": os.fspath(global_rc),
            "npm_config_userconfig": os.fspath(empty_rc),
        }
    )
    global_read = (r1.stdout.strip() == "https://global.registry.invalid/")

    # 2. User overrides global: plain dir, global config, user config
    r2 = run_npm_subprocess(
        config,
        ["config", "get", "registry"],
        plain_dir,
        cache_dir,
        extra_env={
            "npm_config_globalconfig": os.fspath(global_rc),
            "npm_config_userconfig": os.fspath(user_rc),
        }
    )
    user_overrides_global = (r2.stdout.strip() == "https://user.registry.invalid/")

    # 3. Project overrides user: work_dir (has .npmrc), global config, user config
    r3 = run_npm_subprocess(
        config,
        ["config", "get", "registry"],
        work_dir,
        cache_dir,
        extra_env={
            "npm_config_globalconfig": os.fspath(global_rc),
            "npm_config_userconfig": os.fspath(user_rc),
        }
    )
    project_overrides_user = (r3.stdout.strip() == "https://project.registry.invalid/")

    # 4. Env overrides project: work_dir, npm_config_registry set
    r4 = run_npm_subprocess(
        config,
        ["config", "get", "registry"],
        work_dir,
        cache_dir,
        extra_env={
            "npm_config_globalconfig": os.fspath(global_rc),
            "npm_config_userconfig": os.fspath(user_rc),
            "npm_config_registry": "https://env.registry.invalid/",
        }
    )
    env_overrides_project = (r4.stdout.strip() == "https://env.registry.invalid/")

    # 5. CLI overrides env: work_dir, npm_config_registry set, --registry flag passed
    r5 = run_npm_subprocess(
        config,
        ["config", "get", "registry", "--registry=https://cli.registry.invalid/"],
        work_dir,
        cache_dir,
        extra_env={
            "npm_config_globalconfig": os.fspath(global_rc),
            "npm_config_userconfig": os.fspath(user_rc),
            "npm_config_registry": "https://env.registry.invalid/",
        }
    )
    cli_overrides_env = (r5.stdout.strip() == "https://cli.registry.invalid/")

    assertions.append({"name": "global_registry_read", "passed": global_read})
    assertions.append({"name": "user_overrides_global", "passed": user_overrides_global})
    assertions.append({"name": "project_overrides_user", "passed": project_overrides_user})
    assertions.append({"name": "env_overrides_project", "passed": env_overrides_project})
    assertions.append({"name": "cli_overrides_env", "passed": cli_overrides_env})

    return assertions


def scenario_npm12(config, fixtures_dir: Path, sc_scratch: Path, cache_dir: Path, run_npm_subprocess):
    """Execute NPM12 predicates against the selected npm CLI."""
    assertions = []
    work_dir = sc_scratch / "app"
    work_dir.mkdir(parents=True, exist_ok=True)
    bin_dir = work_dir / "node_modules" / ".bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    tool_file = bin_dir / "tool-exec"
    tool_file.write_text("#!/bin/sh\necho \"TOOL_EXEC_SUCCESS:$*\"\n", encoding="utf-8")
    tool_file.chmod(0o755)
    (work_dir / "package.json").write_text(json.dumps({"name": "exec-app", "version": "1.0.0"}, indent=2) + "\n", encoding="utf-8")

    # Local execution with --no
    res1 = run_npm_subprocess(config, ["exec", "--no", "--", "tool-exec", "p1", "p2"], work_dir, cache_dir)
    exec_zero = (res1.returncode == 0)
    stdout_ok = "TOOL_EXEC_SUCCESS:p1 p2" in res1.stdout

    # Missing tool with --offline --no fails closed without network fetch
    res2 = run_npm_subprocess(config, ["exec", "--offline", "--no", "--", "nonexistent-tool-xyz"], work_dir, cache_dir)
    missing_fails = (res2.returncode != 0)

    assertions.append({"name": "local_exec_exit_code_zero", "passed": exec_zero})
    assertions.append({"name": "local_exec_stdout_verified", "passed": stdout_ok})
    assertions.append({"name": "missing_binary_fails_closed", "passed": missing_fails})

    return assertions


SCENARIOS = {
    'NPM01': scenario_npm01,
    'NPM02': scenario_npm02,
    'NPM03': scenario_npm03,
    'NPM04': scenario_npm04,
    'NPM05': scenario_npm05,
    'NPM06': scenario_npm06,
    'NPM07': scenario_npm07,
    'NPM08': scenario_npm08,
    'NPM09': scenario_npm09,
    'NPM10': scenario_npm10,
    'NPM11': scenario_npm11,
    'NPM12': scenario_npm12,
}
