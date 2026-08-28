#!/bin/sh
# one worker process per slot: buildbot runs at most one build per
# (builder, worker) pair, so parallelism needs several workers, not max_builds.
# names must match MOLECULE_WORKERS in master.cfg, hence the shared
# PPG_LOCAL_SLOTS.
set -e

# without it every molecule create fails deep in libvirt, fail here instead
: "${PPG_HYPERVISOR_SSH:?set PPG_HYPERVISOR_SSH, see local/README.md}"

SLOTS=${PPG_LOCAL_SLOTS:-4}
PASS=${PPG_WORKER_PASS:-ppg-local}

i=1
while [ "$i" -le "$SLOTS" ]; do
    d=/bbw/molecule-$i
    mkdir -p "$d"
    [ -f "$d/buildbot.tac" ] \
        || buildbot-worker create-worker "$d" master:9989 "molecule-$i" "$PASS"
    i=$((i + 1))
done

# all but the last daemonize; the last keeps the container alive
i=1
while [ "$i" -lt "$SLOTS" ]; do
    buildbot-worker start "/bbw/molecule-$i"
    i=$((i + 1))
done
exec buildbot-worker start --nodaemon "/bbw/molecule-$SLOTS"
