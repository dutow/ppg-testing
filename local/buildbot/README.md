# Local buildbot for ppg-testing

A two-container buildbot that runs the molecule groups on the local/remote libvirt hypervisor described in `local/README.md`.
Nothing here is generated or duplicated: `master.cfg` imports `tools/render.py` and builds the whole UI (one force scheduler per group, forms from the `params:` blocks) straight from the `scenario.yml` descriptors.

## Prerequisites

* docker with the compose plugin
* a working hypervisor + `PPG_HYPERVISOR_SSH`, see `local/README.md`

```
export PPG_HYPERVISOR_SSH=user@hypervisor-host
```

Until the descriptor work lands on `main`, also:

```
export PPG_TESTING_BRANCH=descriptor-orchestration
```

Builds check out `TESTING_BRANCH` and run `tools/run.py` from it, and neither that nor `local/env.sh` exists on `main` yet, so the default branch fails in the molecule step.

Optional:

| var | default | meaning |
| --- | --- | --- |
| `PPG_SSH_KEY` | `~/.ssh/id_ed25519` | key mounted into the worker, must be authorized on the hypervisor |
| `PPG_LOCAL_SLOTS` | 4 | how many scenarios run in parallel |
| `PPG_TESTING_BRANCH` | `main` | default value of the TESTING_BRANCH form field, wins over the descriptor default |
| `PPG_WORKER_PASS` | `ppg-local` | worker password, only matters if you expose the ports |
| `PPG_BUILDBOT_URL` | `http://localhost:8010/` | base url the UI builds links with |

## Start

```
docker compose -f local/buildbot/docker-compose.yml up -d --build
```

Or `task bot-up`. UI on http://localhost:8010/, no auth (bind it to localhost only).

## Using it

The waterfall/grid stays empty until something is forced. Every group has its own force scheduler named `run-<group>` (slashes to dashes, e.g. `run-pg_tde-tde`):

* **OS** -- multi select, defaults to the group's full os list
* **sequence** -- the sequences declared in the descriptor (`test`, `destroy`, ...)
* **TESTING_BRANCH** -- branch to check out
* one field per descriptor param: choice, boolean or string with the descriptor default. `PLATFORM` and `DESTROY_ENV` are never exposed, `PLATFORM` comes from the selected OS

The OS list is the descriptor's full list, which includes entries the local libvirt backend cannot serve: `rhel-*` (no subscription locally, use rocky instead) and `*-arm`.
`local/env.sh` leaves those image keys unset, so picking them gets you a failure in molecule create, not a skip.

Forcing starts one `group-run` build on the master-local coordinator, which fans out to one `molecule-run` build per selected OS.
Those builds report under the virtual builder name `<group> <os>`, so a partially failing group shows up as per-OS red/green instead of one red blob.
Each of them is a single `tools/run.py --group ... --os <one>` call.

Capacity is `PPG_LOCAL_SLOTS` worker processes in the worker container; the coordinator builds are in-process on the master and only wait, so several groups can be in flight at once.
Both containers read `PPG_LOCAL_SLOTS`, so change it in one place and recreate both.

## Sweeps

Two extra force schedulers run many groups from one button, on the `sweep-run` builder. They fan out the same way, one `molecule-run` build per (group, os), tagged `sweep`, so the grid still shows per-OS red/green.

**release-sweep** -- what to run for a release candidate:

* **groups** -- multi select over every group, defaults to `ppg/pg-*`, `ppg/psp-*`, `pg_tde/*`, `pg_stat_monitor/*` and `psp/*`
* **sequence** -- defaults to `test`
* **VERSION**, **FROM_VERSION**, **REPO** -- set once for every selected group. Empty means "keep whatever the descriptor defaults to", and each group only gets the ones its `scenario.yml` actually declares, so it is safe to select groups with different param sets
* **TESTING_BRANCH**

Mind the scale: the default selection is 37 groups over their full os lists, about 1100 molecule builds, and each one may take up to the 4 hour step timeout. At 4 slots that is not a quick check -- trim the group and os selection unless you really mean the whole matrix.

`VERSION` and `FROM_VERSION` only reach the groups whose descriptor declares them.
`VERSION` reaches 35 groups: all 30 generated `ppg/*` ones plus `pg_tde/tde`, `pg_tde/auxiliary`, `pg_stat_monitor/*` and `psp/server_tests`.
`FROM_VERSION`, `FROM_REPO` and `TO_REPO` reach the 12 `ppg/*-minor-upgrade` and `ppg/*-major-upgrade` groups, which is everything that upgrades anything.
`REPO` reaches the 18 non-upgrade `ppg/*` groups (the upgrade ones take `FROM_REPO`/`TO_REPO` instead), `pg_tde/*` and `pg_stat_monitor/pgsm`.
The generated `ppg/*` defaults come from `ppg/versions.yml` (`default_version`, `default_from_version`), so leaving the sweep fields empty runs each major against its own newest minor.
`ppg/pg-tarballs` is the one hand-written group left with no params, so a sweep cannot pin its version.

A group that does not declare the requested sequence runs `test` instead, which every descriptor has -- better than dropping it from the sweep unnoticed.
`destroy` and `cleanup` are exempt from that fallback: those groups are skipped, because running a full test suite in place of a cleanup is expensive and not what was asked.
Skips are never silent: the sweep build lists them in a `skipped` log, goes orange when it dropped some groups, and fails outright when it dropped all of them, so an empty sweep cannot read as a clean one.
It does happen with the defaults: 6 of the default-selected groups (the `*-minor-upgrade` ones) declare no `cleanup` sequence, so a `cleanup` sweep over the default selection reports them as skipped.
`destroy` is not in the release-sweep dropdown at all -- see below.

**destroy-sweep** -- mop up guests a crashed or cancelled run left behind. Same group select, `sequence` fixed to `destroy` (a `FixedParameter`, so it cannot silently become a test run), no version fields -- guest names do not depend on them. One extra field:

* **BUILD_NUMBER** -- which build's guests to remove, digits only. Empty means this build's own, which is a no-op; to clean up after build 41 of a group, put `41` here. Guest names embed the build number (`name_pattern` `{build}`), so molecule only ever destroys the ones matching it

Trim the group selection before you press it: `BUILD_NUMBER` applies to *every* selected group, and build numbers are per (group, os) builder, so the same number exists for unrelated groups.
A destroy sweep over the whole default selection with `BUILD_NUMBER=41` will happily remove the guests of a *running* build 41 of some group you did not mean to touch.
Select the groups you actually want cleaned.

Cancelling a build in the UI is normally enough on its own: the molecule step gets a SIGTERM first, and `tools/run.py` destroys its guests on the way out.

## Artifacts

Artifacts (molecule.log, report.xml, summary.json) land in the `artifacts` volume, one directory per fan out (the `group-run` or `sweep-run` build number, not the per-os one):

```
/artifacts/<group-slug>/<buildnumber>/<os>/
/artifacts/<group-slug>/sweep-<buildnumber>/<os>/
```

```
docker compose -f local/buildbot/docker-compose.yml exec worker ls -R /artifacts
```

## Caveats

* **builds test committed state only.** The checkout step clones the host repo mount (`/repo`) and checks out `TESTING_BRANCH`, so uncommitted work in your checkout is invisible. Commit first, or run `tools/run.py` directly for edit-test cycles.
* the per-os builds of one fan out share the dir, so the `summary.json` written by `tools/run.py` is whichever os finished last. Per-os results live in the `<os>/` subdirs and in the buildbot build status.
* a descriptor that fails to load is skipped with `skipping <group>: <err>` on the master's stderr, the other groups keep working. If the master container exits right after start, that is a broken config, not a broken descriptor: `docker compose -f local/buildbot/docker-compose.yml logs master`.
* the master works on an rsynced copy of the repo (`/work`), because materializing the generated `ppg/*` groups needs a writable tree and `/repo` is mounted read-only. New or changed descriptors need `docker compose restart master`, not just a reconfig.
* the generated ppg groups are materialized in each build too, so a fresh clone is fine.
* guest names get the buildbot build number as `BUILD_NUMBER`, so parallel runs of the same group and os do not collide on the hypervisor. The group name is only in there for descriptors whose `name_pattern` uses `{job}`; the rest have a hardcoded prefix, so two *different* groups can still overlap if their prefix and os token match.
* only the last worker process is supervised by docker; if one of the others dies the container stays up with reduced capacity. `docker compose restart worker` brings them all back.
