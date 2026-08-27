# Jenkins job migration inventory (ppg/ molecule-driven jobs -> descriptors)

Source: `/storage/pgqa/jenkins-pipelines/ppg/` (86 `.groovy` files, 85 `.yml` job-builder
files). Every `.yml` maps to a `.groovy` via its `script-path` field; basenames match
except `pgpool2-build-RELEASE.yml` -> `pgpool2-build.groovy`. `pgsm-parallel-wip.groovy`
has no `.yml` at all (not wired into Jenkins as a job).

Mechanical first pass (shared-lib functions + MOLECULE_DIR literal per file) via:

```bash
cd jenkins-pipelines/ppg
for f in *.groovy; do
  fns=$(grep -o 'molecule[A-Za-z]*PPG\|installMolecule[A-Za-z]*\|ppgOperatingSystems[A-Za-z]*' "$f" | sort -u | paste -sd,)
  dir=$(grep -o "MOLECULE_DIR = ['\"][^'\"]*['\"]" "$f" | head -1)
  echo "$f|$fns|$dir"
done
```

Files with no molecule shared-lib calls at all are docker-build / packer / CVE-scan /
documentation jobs unrelated to the ppg-testing molecule scenarios; the mechanical pass
alone is enough to classify those as `hand-written-non-molecule`. Everything else was
read in full and compared stage-by-stage against `templates/jenkins/{single,parallel}.groovy.j2`.

Drift protection: `tools/gen_jenkins.py --check` runs in this repo's github workflow
(`.github/workflows/qa-tools.yml`, advisory until both branches merge). On the
jenkins-pipelines side the same check is `ppg/check-generated.sh` -- that repo has no
github ci, so it stays a manual/pre-push check until someone wires it into a ci trigger.

Dispositions:
- **generated** -- this task makes it generated from a `scenario.yml` `jenkins` section.
- **hand-written-needs-render-line** -- molecule-based, stays hand-written for now; a
  later task adds the `tools/render.py` prepare step to it.
- **hand-written-non-molecule** -- build/packer/docker-build/cve/doc jobs, untouched.
- **obsolete-candidate** -- appears dead or superseded by a sibling file; **not decided
  here**, listed below for user confirmation, nothing deleted.

Totals: 10 generated, 25 hand-written-needs-render-line, 7 obsolete-candidate,
44 hand-written-non-molecule (86 total).

## Generated (this task)

| file | shared-lib functions | MOLECULE_DIR | disposition | notes |
|---|---|---|---|---|
| tde.groovy / tde.yml | installMoleculePython(39), moleculeExecuteActionWithScenarioPPG, ppgOperatingSystemsALL | pg_tde/tde | generated | reference group, proven prior to this task |
| tde-parallel.groovy / tde-parallel.yml | installMoleculePython(39), moleculeParallelPostDestroyPPG, moleculeParallelTestPPG, ppgOperatingSystemsALL | pg_tde/tde | generated | reference group |
| tde-auxiliary.groovy / tde-auxiliary.yml | installMoleculePython(39), moleculeExecuteActionWithScenarioPPG, ppgOperatingSystemsALL | pg_tde/auxiliary | generated | matches single template modulo params/normalizations below |
| tde-auxiliary-parallel.groovy / tde-auxiliary-parallel.yml | installMoleculePython(39), moleculeParallelPostDestroyPPG, moleculeParallelTestPPG, ppgOperatingSystemsALL | pg_tde/auxiliary | generated | matches parallel template |
| pgsm.groovy / pgsm.yml | installMoleculePython(39), moleculeExecuteActionWithScenarioPPG, ppgOperatingSystemsALL | pg_stat_monitor/pgsm | generated | job name `ppg` (see Contradictions below) |
| pgsm-parallel.groovy / pgsm-parallel.yml | installMoleculePython(39), moleculeParallelPostDestroyPPG, moleculeParallelTestPPG, ppgOperatingSystemsALL | pg_stat_monitor/pgsm | generated | clean parallel counterpart; `pgsm-multiOS.groovy` is a near-duplicate, see obsolete-candidates |
| pgsm-pgdg.groovy / pgsm-pgdg.yml | installMoleculePython(39), moleculeExecuteActionWithScenarioPPG, ppgOperatingSystemsALL | pg_stat_monitor/pgsm_pgdg | generated | job name `ppg` (see Contradictions below) |
| pgsm-pgdg-parallel.groovy / pgsm-pgdg-parallel.yml | installMoleculePython(39), moleculeParallelPostDestroyPPG, moleculeParallelTestPPG, ppgOperatingSystemsALL | pg_stat_monitor/pgsm_pgdg | generated | job name `ppg-parallel` |
| psp-installcheck-world.groovy / psp-installcheck-world.yml | installMoleculePython(39), moleculeExecuteActionWithScenarioPPG, ppgOperatingSystemsALL | psp/server_tests | generated | |
| psp-installcheck-world-parallel.groovy / psp-installcheck-world-parallel.yml | installMoleculePython(39), moleculeParallelPostDestroyPPG, moleculeParallelTestPPG, ppgOperatingSystemsALL | psp/server_tests | generated | `psp-installcheck-world-multiOS.groovy` is a near-duplicate, see obsolete-candidates |

## Hand-written, needs a render.py line later (molecule-based, structurally deviant)

| file | shared-lib functions | MOLECULE_DIR | disposition | notes |
|---|---|---|---|---|
| ppg.groovy / ppg.yml | installMoleculePython(39), moleculeExecuteActionWithScenarioPPG, ppgOperatingSystemsALL | `ppg/${SCENARIO}` | hand-written-needs-render-line | scenario chosen by a `SCENARIO` job parameter (`ppgScenarios()`), not fixed per group; conditional (`if/else`) display name; no `archiveArtifacts` post step |
| ppg-multiOS.groovy / ppg-multiOS.yml | same + `disableConcurrentBuilds()` | `ppg/${SCENARIO}` | hand-written-needs-render-line | same scenario-param pattern as ppg.groovy |
| ppg-multiOS-parallel.groovy / ppg-multiOS-parallel.yml | same, no `disableConcurrentBuilds()` | `ppg/${SCENARIO}` | hand-written-needs-render-line | same scenario-param pattern; inconsistent with ppg-multiOS.groovy on disableConcurrentBuilds |
| ppg-upgrade.groovy / ppg-upgrade.yml | installMoleculePython(39), moleculeExecuteActionWithScenarioPPG, ppgOperatingSystemsAMD | `ppg/${SCENARIO}` | hand-written-needs-render-line | scenario-param pattern (`ppgUpgradeScenarios()`); single flavor uses `ppgOperatingSystemsAMD()` not ALL |
| ppg-upgrade-multiOS.groovy / ppg-upgrade-multiOS.yml | same + `disableConcurrentBuilds()` | `ppg/${SCENARIO}` | hand-written-needs-render-line | scenario-param pattern |
| ppg-upgrade-parallel.groovy / ppg-upgrade-parallel.yml | same, no `disableConcurrentBuilds()` | `ppg/${SCENARIO}` | hand-written-needs-render-line | scenario-param pattern |
| tde-upgrade.groovy / tde-upgrade.yml | installMoleculePython(39), moleculeExecuteActionWithScenarioPPG, ppgOperatingSystemsALL | pg_tde/upgrade | hand-written-needs-render-line | stage names differ ("Create virtual machine" vs template's "Create virtual machines", "Run upgrade playbook", "Run verification", "Cleanup"); post message uses an em-dash, not template's fixed text |
| tde-upgrade-parallel.groovy / tde-upgrade-parallel.yml | installMoleculePython(39), moleculeParallelPostDestroyPPG, moleculeParallelTestPPG, ppgOperatingSystemsALL | pg_tde/upgrade | hand-written-needs-render-line | slack notification is a large custom function (derived labels, conditional branches) far beyond the simple field-substitution macro |
| tarball.groovy / tarball.yml | installMoleculePython(39), moleculeExecuteActionWithScenarioPPG, ppgOperatingSystemsALL | ppg/pg-tarballs | hand-written-needs-render-line | no `archiveArtifacts` post step at all; one single job fans out to 3 separate SSL-version parallel jobs (not a 1:1 single/parallel pair) |
| tarball-parallel-ssl1.groovy / .yml | installMoleculePython(39), moleculeParallelPostDestroyPPG, moleculeParallelTestPPG, ppgOperatingSystemsSSL1 | ppg/pg-tarballs | hand-written-needs-render-line | one of 3 SSL-version-locked parallel jobs sharing this group; no archiveArtifacts |
| tarball-parallel-ssl3.groovy / .yml | same, ppgOperatingSystemsSSL3 | ppg/pg-tarballs | hand-written-needs-render-line | ditto |
| tarball-parallel-ssl35.groovy / .yml | same, ppgOperatingSystemsSSL35 | ppg/pg-tarballs | hand-written-needs-render-line | ditto |
| psp-performance-test.groovy / psp-performance-test.yml | installMoleculePython(39), moleculeExecuteActionWithScenarioPPG | psp/performance_tests | hand-written-needs-render-line | single job, no parallel counterpart exists at all |
| component-generic.groovy / component-generic.yml | installMoleculePython, moleculeExecuteActionWithScenarioPPG | `${PRODUCT}/setup` | hand-written-needs-render-line | product chosen by a `PRODUCT` job parameter, not fixed per group (same scenario-param family as ppg.groovy) |
| component-generic-parallel.groovy / .yml | installMoleculePython, moleculeParallelPostDestroyPPG, moleculeParallelTestPPG | `${PRODUCT}/setup` | hand-written-needs-render-line | same PRODUCT-param pattern |
| docker-component.groovy / .yml | installMoleculePython, moleculeExecuteActionWithScenarioPPG | `docker/${COMPONENT}` | hand-written-needs-render-line | docker driver, COMPONENT-param pattern |
| docker-component-multiOS.groovy / .yml | installMoleculePython, moleculeParallelPostDestroyPPG, moleculeParallelTestPPG | `docker/${COMPONENT}` | hand-written-needs-render-line | docker driver, COMPONENT-param pattern |
| docker-component-parallel.groovy / .yml | installMoleculePython, moleculeParallelPostDestroyPPG, moleculeParallelTestPPG | `docker/${COMPONENT}` | hand-written-needs-render-line | docker driver, COMPONENT-param pattern |
| docker-server.groovy / .yml | installMoleculePython, moleculeExecuteActionWithScenarioPPG | docker/ppg-docker | hand-written-needs-render-line | docker driver, own job model |
| docker-server-multiOS.groovy / .yml | installMoleculePython, moleculeParallelPostDestroyPPG, moleculeParallelTestPPG | docker/ppg-docker | hand-written-needs-render-line | docker driver |
| docker-server-parallel.groovy / .yml | installMoleculePython, moleculeParallelPostDestroyPPG, moleculeParallelTestPPG | docker/ppg-docker | hand-written-needs-render-line | docker driver |
| docker-server-parallel-generic.groovy / .yml | installMoleculePython, moleculeParallelPostDestroyPPG, moleculeParallelTestPPG | docker/ppg-docker | hand-written-needs-render-line | docker driver |
| docker-server-parallel-custom.groovy / .yml | installMoleculePython, moleculeParallelPostDestroyPPG, moleculeParallelTestPPG | docker/ppg-docker-custom | hand-written-needs-render-line | docker driver |
| docker-server-parallel-custom-upgrade.groovy / .yml | installMoleculePython, moleculeParallelPostDestroyPPG, moleculeParallelTestPPG | docker/ppg-docker-custom-upgrade | hand-written-needs-render-line | docker driver |
| docker-server-parallel-upgrade.groovy / .yml | installMoleculePython, moleculeParallelPostDestroyPPG, moleculeParallelTestPPG | docker/ppg-docker-upgrade | hand-written-needs-render-line | docker driver |

Follow-up candidate patterns worth a dedicated third template flavor (not built in this
task, per instructions -- do not force-fit):
- **scenario-as-parameter**: `MOLECULE_DIR` built from a job parameter instead of being
  fixed per group (`ppg/${SCENARIO}`, `${PRODUCT}/setup`, `docker/${COMPONENT}`). Seen in
  `ppg*`, `ppg-upgrade*`, `component-generic*`, `docker-component*` -- 4+ job families.
- **docker driver family**: `docker-server*`/`docker-component*` all use the docker
  driver with its own stage shape (image build + run), distinct from the AWS
  single/parallel templates. 7 files.

## Obsolete candidates (redundant/dead -- listed for user confirmation, nothing deleted)

| file | shared-lib functions | MOLECULE_DIR | notes |
|---|---|---|---|
| tde-multiOS.groovy / tde-multiOS.yml | installMoleculePython(39), moleculeParallelPostDestroyPPG, moleculeParallelTestPPG, ppgOperatingSystemsALL | pg_tde/tde | byte-identical to tde-parallel.groovy except one extra `disableConcurrentBuilds()` line; both wired as live Jenkins jobs today |
| pgsm-multiOS.groovy / pgsm-multiOS.yml | installMoleculePython(39), moleculeParallelPostDestroyPPG, moleculeParallelTestPPG, ppgOperatingSystemsALL | pg_stat_monitor/pgsm | near-duplicate of pgsm-parallel.groovy: extra `disableConcurrentBuilds()`, DESTROY_ENV re-added as a (broken, unused by post block) string param |
| psp-installcheck-world-multiOS.groovy / .yml | installMoleculePython(39), moleculeParallelPostDestroyPPG, moleculeParallelTestPPG, ppgOperatingSystemsALL | psp/server_tests | near-duplicate of psp-installcheck-world-parallel.groovy: extra `disableConcurrentBuilds()` |
| tarball-multiOS-ssl1.groovy / .yml | installMoleculePython(39), moleculeParallelPostDestroyPPG, moleculeParallelTestPPG, ppgOperatingSystemsSSL1 | ppg/pg-tarballs | near-duplicate of tarball-parallel-ssl1.groovy: extra `disableConcurrentBuilds()` |
| tarball-multiOS-ssl3.groovy / .yml | same pattern, ppgOperatingSystemsSSL3 | ppg/pg-tarballs | near-duplicate of tarball-parallel-ssl3.groovy |
| tarball-multiOS-ssl35.groovy / .yml | same pattern, ppgOperatingSystemsSSL35 | ppg/pg-tarballs | near-duplicate of tarball-parallel-ssl35.groovy |
| pgsm-parallel-wip.groovy (no .yml) | installMoleculePython(39), moleculeParallelPostDestroyPPG, moleculeParallelTestPPG, ppgOperatingSystemsALL | pg_stat_monitor/pgsm | not wired to any Jenkins job at all (no .yml); "wip" in the name; has extra ad-hoc log-retrieval/archive stages not seen elsewhere |

The `-multiOS` vs `-parallel` duplication (identical file except one extra
`disableConcurrentBuilds()` line) recurs 5 times across 3 different groups (tde, pgsm,
psp-installcheck-world) plus all 3 tarball SSL variants -- consistent with `-parallel`
being a later rename/refresh of `-multiOS` that never got its predecessor deleted. Not
acted on here; flagging for user confirmation before any deletion.

## Contradiction note (not blocking, pre-existing)

`tde.yml`, `pgsm.yml` and `pgsm-pgdg.yml` all declare `name: ppg` (same Jenkins job name,
different `script-path`/file). This predates this task (present before `f1cebb2e`, the
most recent commit touching these files) and is reproduced verbatim since it's a
pre-existing production condition, not something introduced by generation. It is *not*
the "two jobs claim the same output filename" contradiction this task's escalation rule
is about -- the three `.yml` files have distinct filenames and each writes its own
target path; only the in-Jenkins job *name* collides. Flagging for awareness, not
blocking generation.

## Hand-written, non-molecule (build/packer/docker-build/cve/doc jobs -- untouched)

No shared-lib molecule functions found by the mechanical pass; spot-checked a sample
(pg_tde.groovy, postgresql_server.groovy, ppg-server.groovy, ppg-docker.groovy,
docker-cve-scan.groovy) and confirmed they build/package/scan via `docker run` +
builder scripts, unrelated to ppg-testing molecule scenarios.

component-multi-parallel.groovy, docker-cve-scan.groovy, etcd.groovy,
get-pg_stat_monitor-branches.groovy, haproxy.groovy, llvm.groovy, patroni.groovy,
percona-postgis.groovy, pgaudit.groovy, pgaudit_set_user.groovy, pgbackrest.groovy,
pgbadger.groovy, pgbouncer.groovy, pg_cron.groovy, pg_gather.groovy,
pg_percona_telemetry_autobuild.groovy, pgpool2-build.groovy (+ pgpool2-build-RELEASE.yml),
pgrepack.groovy, pg_snyk_scan.groovy, pg_source_tarballs.groovy,
pg_stat_monitor-autobuild.groovy, pg_tarballs.groovy, pg_tde.groovy, pg_tde_nightly.groovy,
pgvector.groovy, postgis_tarballs.groovy, postgresql-common.groovy, postgresql-ivee.groovy,
postgresql_server.groovy, postgresql_server_nightly.groovy, ppg-11-documentation-md.groovy,
ppg-12-documentation-md.groovy, ppg-13-documentation-md.groovy, ppg-14-documentation-md.groovy,
ppg-docker.groovy, ppg-pgbackrest-docker.groovy, ppg-pgbouncer-docker.groovy,
ppg_release.groovy, ppg-server.groovy, ppg-server-ha.groovy, pysyncobj.groovy,
timescaledb.groovy, wal2json.groovy, ydiff.groovy (44 files).

Also untouched: the `packer/` subdirectory (AMI/image-factory tooling, not job groovy).

## Groups descriptor-ized in this task

| group | jenkins jobs produced | jenkins job names |
|---|---|---|
| pg_tde/tde | tde.groovy/.yml, tde-parallel.groovy/.yml | ppg, tde-parallel |
| pg_tde/auxiliary | tde-auxiliary.groovy/.yml, tde-auxiliary-parallel.groovy/.yml | tde-auxiliary, tde-auxiliary-parallel |
| pg_stat_monitor/pgsm | pgsm.groovy/.yml, pgsm-parallel.groovy/.yml | ppg, pgsm-parallel |
| pg_stat_monitor/pgsm_pgdg | pgsm-pgdg.groovy/.yml, pgsm-pgdg-parallel.groovy/.yml | ppg, ppg-parallel |
| psp/server_tests | psp-installcheck-world.groovy/.yml, psp-installcheck-world-parallel.groovy/.yml | psp-installcheck-world, psp-installcheck-world-parallel |

pg_tde/tde was already descriptor-ized before this task and is included above for
completeness (its files were regenerated and re-verified `--check`-clean as part of this
task's generation run).

## Schema/tooling extensions added in this task

- `tools/gen_jenkins.py` `resolve_params()`: added `default_<flavor>` support, mirroring
  the existing `description_<flavor>` override. Needed because `pg_stat_monitor/pgsm_pgdg`'s
  `PGSM_BRANCH` and `VERSION` params carry different defaults between the single and
  parallel live jobs (e.g. `ppg-18.4` vs `pg-18.4`), same kind of single/parallel drift
  `description_parallel` already exists to handle.
- `tools/extract_descriptors.py`: `--write` now merges extracted render keys with any
  unknown top-level keys already present in an existing `scenario.yml` (`params`,
  `jenkins`, ...) instead of overwriting the file wholesale. The `pg_tde/tde` hard-skip
  was removed since preservation makes it redundant -- the extractor now safely rewrites
  every group's render keys while carrying params/jenkins sections forward untouched.
  Added `tools/tests/test_extract_descriptors.py` covering the merge directly and a
  round-trip through `process_group()` with a fake `jenkins` section.
- No `os_list_fn` template knob was needed: none of the 5 in-scope groups use a
  non-default `ppgOperatingSystems*()` function for their `PLATFORM` choices or test/destroy
  calls (all use `ppgOperatingSystemsALL()`).

## Normalizations (expected, harmless diffs from regeneration)

Every hunk in the generated jenkins-pipelines diff is one of: the `// GENERATED ...`
header line, the `sh "python3 tools/render.py --group <dir>"` prepare step, or one of
these normalizations:

| file(s) | what changed | why harmless |
|---|---|---|
| tde-auxiliary.groovy, tde-auxiliary-parallel.groovy | `string(...)` param fields reordered from `name, defaultValue, description` to the template's canonical `defaultValue, description, name` | pure field reordering inside the same `string(...)` call; Jenkins Job DSL/Groovy named-argument calls are order-independent, values unchanged |
| tde-auxiliary.groovy, tde-auxiliary-parallel.groovy | `IO_METHOD` choice list `['sync', 'worker', 'io_uring']` (one line) pretty-printed to one value per line | template always renders `choices:` as a multi-line array; content/order unchanged |
| psp-installcheck-world-parallel.groovy | `archiveArtifacts(...)` closing `)` indentation fixed from 11 to 12 spaces | pre-existing typo in the live file; template always emits consistent 4-space-step indentation |

All other in-scope files (tde.groovy/tde-parallel.groovy, pgsm.groovy/pgsm-parallel.groovy,
pgsm-pgdg.groovy/pgsm-pgdg-parallel.groovy, psp-installcheck-world.groovy) had param
blocks already in the template's canonical field order/formatting, so their diffs are
exactly the header line + render step, nothing else.

Regenerate this diff yourself with:

```
python3 tools/gen_jenkins.py --jenkins-repo <path-to-jenkins-pipelines>
git -C <path-to-jenkins-pipelines> diff master
```
