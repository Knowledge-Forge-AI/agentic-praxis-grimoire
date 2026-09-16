"""Frozen APG138 inheritance and exact schema vocabulary (standard library only)."""
from __future__ import annotations

import hashlib
import json

PROVISIONAL = ('astro-profile', 'browser-runtime-profile', 'chatgpt-manager-workflow', 'composing-approved-roadmap-assignments', 'converting-bash-scripts-to-python', 'css-language-profile', 'dockerfile-profile', 'go-cmp-test-profile', 'go-language-profile', 'go-test-profile', 'gomock-test-profile', 'javascript-language-profile', 'jsx-language-profile', 'markdown-language-profile', 'mdx-profile', 'minitest-test-profile', 'nix-test-profile', 'nodejs-runtime-profile', 'npm-package-manager-profile', 'playwright-test-profile', 'postgresql-database-profile', 'pytest-test-profile', 'react-component-profile', 'ruby-language-profile', 'sqlite-database-profile', 'svg-language-profile', 'typescript-language-profile', 'vagrantfile-profile', 'vite-build-profile', 'vitest-test-profile', 'web-accessibility-profile')
HISTORICAL_EXCLUSIONS = ('APGR-CAP1', 'APGR-CXT-FOOTPRINT', 'APGR-DEBT-JS-QD-001', 'APGR-DEBT-JS-QD-002', 'APGR-DEBT-JS-QD-003', 'APGR-DEBT-JS-QD-004', 'APGR-PUBLICATION-LINT', 'APGR-REPORT-GO', 'APGR-REPORT-IDEMPOTENCY', 'APGR-REPORT-OPS-SEMANTICS', 'APGR-REPORT-STALELOCK', 'APGR-REPORT-VERIFIER', 'SKILL-A11Y', 'SKILL-BROWSER', 'SKILL-NPM-PKG', 'SKILL-PLAYWRIGHT', 'SKILL-SVG', 'SKILL-VITE')
ITEM_BINDINGS = {
    'APGR-CI-QUAL': '1ecf58c060cb8e258b6908e2220ad1ac38e28e12d073553f744a9e9935378365',
    'APGR-CXT-BUDGET-COMPRESSION': 'cb25fc5ab5bd6138e483f1a8cdbaf2aac29d657cb36a388dc10382fd284645cc',
    'APGR-CXT2B': 'a0a54c9e922abc7b4b2f48dd0e63c954fa7eb50ac774b7ce5b2a1dd29fdfaf01',
    'APGR-DEBT-CSS-QD-001': 'a667ab2f0bd71d734e174abeb2623ee87f3930defc8b968e275afcedd22e2a62',
    'APGR-DEBT-CSS-QD-002': '4a870b1908ff37c0893b8dfc8b202a234c6a979aee837c3bb164c1b7e4a81780',
    'APGR-DEBT-CSS-QD-003': '781e2343f5890573864d72d6c2b9072cdcd492867636e026aff8a13a2d1d1fe7',
    'APGR-DEBT-CSS-QD-004': '25062c380b19774cdbede9a32cc2aa1e654d6d64749009073c07993d79b46ead',
    'APGR-DEBT-CSS-QD-005': '943f15ac8d36198627fff8569996840584aecb16291f34924a673f1c11f18068',
    'APGR-DEBT-JS-QD-005': '54ae23e6165a9a9c4255ac1d369cf6664b1231cd3be5d88260dcaea6168e144c',
    'APGR-HOTSPOT-CHURN': 'ea099d85f58b5e70b872d00c3faf5efc3eb4387543161f5c6a010ad379fff21a',
    'APGR-REPORT-OUTBOX': 'c6f23aaab4f61da10ccf2c1ce7a38aadb91dd310bc81383b4272b43e1cffe96e',
    'APGR-REPORT-PROJECT-KEY': '1fcd499aed7e76570baa03d925e292cb6d2028154d73167b3d8e39844f81e722',
    'APGR-REPORT-PUREGO-GIT': 'e6dd9b8f8caf999a575597ef2c5783dfa5c02269d43fe8d53cff2395b1de902b',
    'APGR-REPORT-RESULT-FIELDS': 'af69f8ce3560bfa1639a0b29ff436b7bf027b098e09552f60d7a5928d4836046',
    'APGR-XO-COMPAT': 'b90ddb7ebe40356f25cd592d09950bf66d1a5b165f7868f7570c081b836afe54',
    'MATURITY:astro-profile': 'c146a7afe5f5161d92e9de7b9eaa6b753583db2e6c9642c7de1f541236311aa1',
    'MATURITY:browser-runtime-profile': 'f8aa8fcb5cde217f8ad2536de7b533570a05f124b716156482c587eb081b4e65',
    'MATURITY:chatgpt-manager-workflow': '3e445f131ae5b7438b36ed84618c47a6ac71907bd0ef41152ffa87d94a06bec4',
    'MATURITY:composing-approved-roadmap-assignments': '14dc61f5406d8593f17d61df5d66cffd6f86c41d9ba7a034128ff45988f7de7b',
    'MATURITY:converting-bash-scripts-to-python': 'a89dbc92971fb4b2393440e0a2bb00b36afdd3ccc1449841ed9d3ebfe63e825e',
    'MATURITY:css-language-profile': '3c91b56a8be2899c39d5bef116b26bd34c7c902fcafaf4b183814bd78f478be2',
    'MATURITY:dockerfile-profile': 'd0d690b0d849100c2465e056c66cc958c1784092eb6acf7fad55950cd723aa57',
    'MATURITY:go-cmp-test-profile': '5e44c819ce20f3c2bc97c34d228dd0cd14bf5028996aea3ace3ce2217fe269ce',
    'MATURITY:go-language-profile': 'eee5d112d4e15676697042fba8a7a3e8f5e5c461ccca2c835b47ba961e981222',
    'MATURITY:go-test-profile': '6ac58aee1692ebd8ffa8b6229886003d763d52b020fb11c078093d266aa3c307',
    'MATURITY:gomock-test-profile': 'a95947f7b9c82045bccad739d3577c8c5402031edcfead0843511a00f24e6fe8',
    'MATURITY:javascript-language-profile': '10e34e2d0665171b269215e91032dd88b8076b0b8770d00e2ef396b7135741da',
    'MATURITY:jsx-language-profile': '820e3493890b50ce1adfab00f4c069780f524e7969596cf93ed5bdeed0100b18',
    'MATURITY:markdown-language-profile': '16acbe7e021b07999b5b8275fff770d2b4a2b69b3825df7ac27b8f41d7ff7598',
    'MATURITY:mdx-profile': '7ba9b0de962ac6cbd9875bf1efa1da39cf1a0a408de499f26926323249de9e88',
    'MATURITY:minitest-test-profile': '1981a78cd1f2dd17f455051a2d1fe500c8b2e38ddeb243ce80b1be47b618d881',
    'MATURITY:nix-test-profile': '54bc2fa20ac47d06583f5ee79761df8d0b6a6b602967f5e813eff84f03a1a452',
    'MATURITY:nodejs-runtime-profile': 'cfdbd5facebf81473edb63673b04a6c4adaacf3fce3f5449e5458787d62a6c87',
    'MATURITY:npm-package-manager-profile': '0c5f9fb68e75801dd9b1f3e6874e025418071710c5597b99579886d6f83cbfc7',
    'MATURITY:playwright-test-profile': '24a22de93505aec446bc347e4e1a1ff5777d0131631cf2abffdf3926500a032e',
    'MATURITY:postgresql-database-profile': '1e5635be20fdefdb9c7256722621a3ba8cc3f53a29a0af5380ec9161715d5ed1',
    'MATURITY:pytest-test-profile': '812e95aa193138b244d4400632d0a5eb5987d08d76cb990537e409fdb20c6852',
    'MATURITY:react-component-profile': '73071779d6c824ae3d8eb99976c6a85d43a025783abb355f9b754fc87bdd1cde',
    'MATURITY:ruby-language-profile': '0ba543f736b701f07138b899edbbdafdf9863409ae0bcdb2d9fadac81cfcf26c',
    'MATURITY:sqlite-database-profile': '6bf86ccea7be2478000243e714d699ed8727ee2ca3fd988f7a568662763ce741',
    'MATURITY:svg-language-profile': '2224208123fbd25b33b237d2faa605fb8de8869ec7a374ac3bc01eef2dab958a',
    'MATURITY:typescript-language-profile': '841c65b2e5b4a6663ced138d0c984e004057f7706d1c78bb42c15f2709908030',
    'MATURITY:vagrantfile-profile': '6e0f5e413f9d9dd4c596106abe3281396138fc2af9d3796cd7feebf8ac326ef4',
    'MATURITY:vite-build-profile': '3df105bdfe60fd37e590e45d7d5e4b19edc78c7e3e1301c7790de5fcfc0abf04',
    'MATURITY:vitest-test-profile': '614d768bc6967369d466967a687fe811bc781c25d0541e1dc66f88d561fd6584',
    'MATURITY:web-accessibility-profile': 'f736d814a521bb0e5d64f4ff367c44659071eb8fa78303dc62f4389d19632a4e',
    'RM-S0': '98a7ea65c93a8a1e2dc69a58ee91231716e3155f3558b99c2e9ae17ff27d8b0f',
    'RM-S1': '348fa37aee8c55a848a12b05c13ed063778c44b46660aafeb75874875ca7963a',
    'RM-S2': '5c0274f110144484af918c2fbd7092d9288cb71517c23ab6b18bdca59d19575b',
    'RM-S3': '862d322a03fbcfa891a6df5bd9d98ea247bbabacf7f7750d904353cb9ef869ad',
    'RM-S4': 'ec342d15b96fea923f29d462cef47bf9b0c647b8a97be5a93f004ecac9bd8071',
    'RM-S5': '9421c7ac3e81297b10c4cbf9aa940d07953b43569818fa81a2ff83ef0b1cecce',
    'SKILL-KG-QUALITY': 'a3a15c749cf1e0d107931eb4aed988dba2cfa5047041640f8a8bbb45d98f48b2',
    'SKILL-MIGRATION': 'bb5bc5ea28cc530348c890616fcd69c08accc861a994dc4b0eb722d3141b8251',
    'SKILL-VER-PROTO': 'fc957456e1fc3a998e923e99047abab47841700a3cda176ab23629d271fc4b7d',
}
TRIGGER_BINDINGS = {
    'CSS-QD-001': 'b054788a71766e2fe92e09c77d57d69862cb0b298b4e575bb069e519199e1d21',
    'CSS-QD-002': 'dfa6e7ab4a2038eae3fc4a2c48eb61851a6ee690d989deb0cc180db238f226db',
    'CSS-QD-003': 'b126d8c7ccdc8bfc729a537f74c5153dfa8ceb1af0ae65e0d8bab84e018e5cce',
    'CSS-QD-004': 'e0cc27fd313a5bb513425053e8a4fd3289c02f35cf11e6f469dd02a60f9a664d',
    'CSS-QD-005': 'd916dfe5b7df9cbc8e1458f5e7d03bf8ac76bbfe7eb7b9a0a7c9fb2be3450b87',
    'JS-QD-005': 'b35e70302e39228767d4ad2ae07ed15eaf65ddde8b6c984e3e5f1403f9c927ee',
    'APGR-REPORT-PUREGO-GIT': 'edf48e0011ea68043d64160c2218b188b008496f667eb49754aae6779cf4341f',
    'SKILL-MIGRATION': 'f29146320b1c31dd3082db948c98745f54bf7ecd4b25430596eb673c9a1247a5',
    'APGR-CXT-BUDGET-COMPRESSION': 'a0d1fdbfc7eefdaed8205248ed91e74381065b4eeeb75267cbcf3f85742c68dd',
}

EVIDENCE_CATEGORIES = ("repeated_positive_use", "representative_non_triggers",
    "defect_debt_disposition", "rollback", "provenance", "independent_review", "current_validation")

# APG139 maturity reopening conditions are separate from frozen debt refreshes.
MATURITY_TRIGGER_BINDINGS = {'MATURITY:astro-profile': '70ae9eda0529e775cc1986b7c0de78f9465e11597c57531d72b368f01b0420f7',
 'MATURITY:browser-runtime-profile': '55daa664b2f093693d952e8818ee68d68f71301e0e275e5144b59ec5e2adfab2',
 'MATURITY:chatgpt-manager-workflow': 'eb126a43ae1c3fee1c3db9215085c169b4dc4f03429e9c1881628e8d50c932df',
 'MATURITY:composing-approved-roadmap-assignments': 'e172cd721b63949c4ab1bdedac11f4bd3d4fc37dc2c380e0d4e66c929e4cdb03',
 'MATURITY:converting-bash-scripts-to-python': 'baf981947da84dcdd881813cac7889e91736ee9649940e800b1f13d8ea0d87c0',
 'MATURITY:css-language-profile': '1b21af35e116b8952b8d3645af6e43a6c331064d9531d00f9fdaf899fa751a5c',
 'MATURITY:dockerfile-profile': '2850ae38554056a22a5ba8f1ef0a7df0908f753acefb60ad86381a4a35cab8c0',
 'MATURITY:go-cmp-test-profile': '4cf2049ae1f93eb06c4775fa583880f058c7c6fa1dc1da917987a1005c646fa2',
 'MATURITY:go-language-profile': 'f60010064f80edcd9d1f5bc6c46c65f40068298b713f226b6314a95cf3f8d334',
 'MATURITY:go-test-profile': 'e5970b0e29ec581cfbe4c74485989fc304dde8be73f3dc8df9adafc252663c54',
 'MATURITY:gomock-test-profile': '53b6f4e5685726452d071c4938a9972379a5cf014b7820193544fdd397cc53a6',
 'MATURITY:javascript-language-profile': '0a8741107719a065ff9c2bf0258f7fa59c7e967c778ca9ef206544f7ffa52ce3',
 'MATURITY:jsx-language-profile': 'f063989c39316d512924f84c13d7e3d2b64a4fa87c957dc45ee19f263ba0fb02',
 'MATURITY:markdown-language-profile': '5fa8f1779dbd162ab7dbb70aef7871fce4ce08f7048252cf32e2224f1ce3fc07',
 'MATURITY:mdx-profile': '31a33a21afd95a20bdcb18516f4483d64e29706c5b86cffe32326c73aa1e7ab3',
 'MATURITY:minitest-test-profile': '14740de0e9d37d69d145de410480a959d8d286e856c5c0b4e9892b67cad94359',
 'MATURITY:nix-test-profile': 'f8ce7fd061e74239533bb65204f6e5508e8e7090f0790fb9197d2ba8eae30951',
 'MATURITY:nodejs-runtime-profile': '481215ca31eb4bd771dbf296362168d0485322f4a332c71c4651b20a5432af58',
 'MATURITY:npm-package-manager-profile': '6abea193ddd7eed15b4af94ca8fefe0b4c1dbb7ab54af0ded39af99a6a35a766',
 'MATURITY:playwright-test-profile': 'd5b0dbdba4070a9f4c60dcf503901082ed98291ab8437ae5f123c90320733665',
 'MATURITY:postgresql-database-profile': '5344a75364cd418a2c48545469d3522bda28247ef4f85054a7688e4b9be77d06',
 'MATURITY:pytest-test-profile': 'fdb2a5e0b89e15481663ada7f1d4f2411d68e6cf26e10361466e6bbc45aff8fa',
 'MATURITY:react-component-profile': 'a4b660a59ae8d83edfd911ef3351a46a61d15c4dc16d4c4b702adc011b6663c1',
 'MATURITY:ruby-language-profile': '718cf5ee2d8b59e561c52836508cc8eb4ba5588c010d030cd7e542c84b21ef16',
 'MATURITY:sqlite-database-profile': '257474a855394e1dcf7b646700535af81a35588167130b467ce793e920415cc8',
 'MATURITY:svg-language-profile': '65f0ec3c7f451d1d09fdcb2415eff9a587e71d41ae9bba7072defc85c4cfd289',
 'MATURITY:typescript-language-profile': '6fdf6bf76e586b4418e660495f07a4e85753fa095b930a3832399961e8fdfff3',
 'MATURITY:vagrantfile-profile': 'b979ee67c72dedf5a7e5cb081b882e97551077aacd645cbefc4263c9a0731798',
 'MATURITY:vite-build-profile': '7c604a02f515d83ea76190279d1871a7c3178d6228842ca8f9184e1c80d31840',
 'MATURITY:vitest-test-profile': 'b2877092b28794868abb05148971190de6f7b087713f94acebf8c5490874409f',
 'MATURITY:web-accessibility-profile': '2374b81359d334860d6a60bdc3d3c9bb3a3f3773f36882145dd4898eaec6cfea'}
DEBT_AUTHORITY = "docs/governance/language-profile-known-debt.json"

def fingerprint(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode()).hexdigest()


def obj(properties: dict) -> dict:
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


def array(items: dict) -> dict:
    return {"type": "array", "items": items, "uniqueItems": True}


def enum(*values: str) -> dict:
    return {"type": "string", "enum": list(values)}


def nullable(shape: dict) -> dict:
    return {"anyOf": [shape, {"type": "null"}]}


TEXT = {"type": "string", "minLength": 1}
BOOL = {"type": "boolean"}
TEXTS = array(TEXT)
DISPOSITION = nullable(obj({
    "decision_ref": TEXT, "qualification_refs": TEXTS, "review_ref": TEXT,
    "rationale": TEXT, "maintenance_ref": nullable(TEXT),
    "compatibility_ref": nullable(TEXT), "maturity_ref": nullable(TEXT),
}))
ROW_SCHEMAS = {
    "closure": obj({
        "item_id": TEXT, "sources": TEXTS,
        "inherited_class": enum("EXTERNAL_GATE", "CONDITION_TRIGGERED", "OPTIONAL_LATER", "PROVISIONAL_MATURITY"),
        "closure_phase": enum("V0110-B", "V0110-C", "V0110-D", "V0110-E"),
        "allowed_outcomes": TEXTS, "prerequisites": TEXTS,
        "trigger_ref": nullable(TEXT), "consequence": TEXT,
        "status": enum("OPEN", "DELIVERED", "REJECTED", "CONSUMER_HANDOFF_CLOSED", "MAINTENANCE_TRIGGER",
                       "STABLE", "PROVISIONAL_MAINTENANCE", "DEPRECATED_OR_SUPERSEDED"),
        "disposition": DISPOSITION,
    }),
    "maintenance": obj({
        "trigger_id": TEXT, "owner": TEXT, "source_authority": TEXTS,
        "refresh_condition": TEXT, "repair_condition": TEXT,
        "current_state": enum("FALSE", "TRUE", "UNKNOWN"), "state_evidence": TEXTS,
        "interpretation": TEXT, "affected_behavior": TEXT, "affected_skills": TEXTS, "blocks_stable": BOOL,
        "evidence_required": TEXTS, "refresh_procedure": TEXT,
    }),
    "compatibility": obj({
        "watch_id": TEXT, "apgr_identity": TEXT, "consumer_project": TEXT,
        "observed_revision": nullable(TEXT), "observed_contract": nullable(TEXT),
        "observation_date": nullable(TEXT), "fixture_identity": nullable(obj({"path": TEXT, "sha256": TEXT})),
        "inherited_item_ids": TEXTS,
        "status": enum("WATCH", "QUALIFIED", "HANDOFF_CLOSED"),
        "supported_cases": TEXTS, "unsupported_cases": TEXTS, "ownership_split": TEXT,
        "refresh_owner": TEXT, "refresh_trigger": TEXT, "source_authority": TEXTS,
        "qualification_evidence": TEXTS, "adoption_claimed": {"const": False, "type": "boolean"},
    }),
    "maturity": obj({
        "skill_id": TEXT, "path": TEXT, "current_maturity": enum("stable", "provisional", "deprecated"),
        "blocking_debts": TEXTS, "debt_authority": {"type": "string", "const": DEBT_AUTHORITY},
        "active_debts": TEXTS, "resolved_debts": TEXTS, "source_references": TEXTS,
        "required_evidence_categories": TEXTS,
        "evidence": obj({name: TEXTS for name in EVIDENCE_CATEGORIES}),
        "independent_review": nullable(TEXT), "next_lifecycle_trigger": TEXT,
        "disposition_status": enum("EXISTING_STABLE", "PENDING_V0110_B", "STABLE", "PROVISIONAL_MAINTENANCE", "DEPRECATED_OR_SUPERSEDED"),
        "maintenance_ref": nullable(TEXT),
    }),
}
FILES = {
    "closure": ("v0-11-closure-ledger", "items", "item_id"),
    "maintenance": ("maintenance-triggers", "triggers", "trigger_id"),
    "compatibility": ("external-compatibility", "watches", "watch_id"),
    "maturity": ("skill-maturity-ledger", "skills", "skill_id"),
}


def schema(kind: str) -> dict:
    filename, key, _ = FILES[kind]
    properties = {"schema_version": {"const": "apg." + kind + "-ledger/v1", "type": "string"},
                  "release": {"const": "v0.11", "type": "string"},
                  "owner_phase": TEXT, key: array(ROW_SCHEMAS[kind])}
    if kind == "closure":
        properties["historical_exclusions"] = TEXTS
    return {"$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": filename, **obj(properties)}


# Forward foundation surface; the immutable v0.10 release inventory is unchanged.
FOUNDATION_FILES = (
    "docs/v0-11-roadmap.md",
    "docs/governance/v0-11-closure-governance.md",
    "docs/adr/2026/09/0055-v0-11-capacity-and-closure-governance.md",
    "docs/evaluations/apg138-v0-11-foundation-closure.md",
    "docs/status/2026/09/12/00183-apg138-v0-11-foundation-closure-exit.md",
)

OUTCOME_EVIDENCE = {
    "DELIVERED": ("implementation", "qualification", "compatibility", "rollback"),
    "REJECTED": ("evaluation", "rejection_rationale"),
    "CONSUMER_HANDOFF_CLOSED": ("provider_delivery", "ownership"),
    "MAINTENANCE_TRIGGER": ("trigger_observation", "refresh_procedure", "independent_review"),
    "STABLE": EVIDENCE_CATEGORIES,
    "PROVISIONAL_MAINTENANCE": EVIDENCE_CATEGORIES,
    "DEPRECATED_OR_SUPERSEDED": ("evaluation", "replacement_or_retirement", "rollback"),
}


def decision_schema() -> dict:
    return {"$schema": "https://json-schema.org/draft/2020-12/schema",
            "anyOf": [obj({
                "schema_version": {"type": "string", "const": "apg.roadmap-decision/v1"},
                "item_id": TEXT, "outcome": {"type": "string", "const": outcome},
                "closure_phase": enum("V0110-B", "V0110-C", "V0110-D", "V0110-E"),
                "author": TEXT, "reviewer": TEXT,
                "evidence": obj({category: TEXTS for category in categories}),
            }) for outcome, categories in OUTCOME_EVIDENCE.items()]}


def maturity_candidate_schema() -> dict:
    """Evidence inventory for review; deliberately not a terminal decision receipt."""
    return obj({
        "schema_version": {"type": "string", "const": "apg.maturity-candidate/v1"},
        "phase": {"type": "string", "const": "APG139"},
        "skill_id": enum(*PROVISIONAL), "proposed_outcome": enum("PROVISIONAL_MAINTENANCE"),
        "review_status": enum("PENDING_DISPATCHER_PRE_FINAL"),
        "independent_review": {"type": "null"},
        "evidence": obj({category: obj({
            "assessment": enum("SUPPORTED", "LIMITED", "MISSING", "PENDING"),
            "references": TEXTS, "observation": TEXT,
        }) for category in EVIDENCE_CATEGORIES}),
        "next_lifecycle_trigger": TEXT, "controlling_debt_ids": TEXTS,
        "consumer_limitations": TEXT, "rationale": TEXT,
    })
