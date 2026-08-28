# Local molecule runs on libvirt

Run any ppg-testing molecule scenario on a local or remote kvm/libvirt machine instead of AWS.
No changes to the scenario molecule.yml files -- the backend is selected by the `driver` env var, which `local/env.sh` sets for you.
Proven: pg_tde full `molecule test` green on debian-13, ubuntu-jammy, rocky-9 and ol-9, roughly 9-23 minutes per scenario.

## Hypervisor host setup

The machine that runs the VMs needs:

* libvirt and qemu/kvm installed
* a user in the `libvirt` group, reachable over ssh with key auth
* an active `default` NAT network and a `default` dir storage pool

If the default network is not active yet:

```
virsh net-start default
virsh net-autostart default
```

If there is no `default` pool:

```
virsh pool-define-as default dir --target /var/lib/libvirt/images
virsh pool-build default
virsh pool-start default
virsh pool-autostart default
```

The pool commands also work remotely over qemu+ssh as an unprivileged libvirt-group user.

### Firewall gotcha with docker

If docker runs on the hypervisor host, it sets the iptables FORWARD policy to DROP, and libvirt with the nftables backend does not counter that.
Guests still get DHCP and DNS (that is host-input traffic), but no internet egress.
The symptom is prepare/converge looking "hung": the apt task retries 60 times and each attempt stalls for minutes in apt/dnf retries.
Diagnosis: from a guest, `ping 8.8.8.8` fails but DNS resolves.
Fix (as root on the host):

```
iptables -I DOCKER-USER -i virbr0 -j ACCEPT
iptables -I DOCKER-USER -o virbr0 -j ACCEPT
```

This is NOT reboot-persistent.
Persist it with whatever your distro uses, e.g. a small systemd oneshot ordered after docker.service, or firewalld direct rules.

## Runner setup

The runner is where molecule runs.
It can be the hypervisor host itself, or any machine/container with ssh access to it.
It needs the virsh client, genisoimage and an openssh client.
xorriso's `xorriso -as mkisofs` emulation works as genisoimage, the version string then reports xorriso.

Use a python venv with molecule 3.3.0 for CI parity:

```
python3 -m venv ~/.venvs/ppg-molecule
. ~/.venvs/ppg-molecule/bin/activate
pip install 'molecule==3.3.0' 'PyYaml==5.3.1' pytest-testinfra pytest 'ansible<10.0.0'
```

On python 3.14 two extra pins were needed: `setuptools<81` (molecule imports pkg_resources) and `ansible-lint<6` (molecule 3.3 imports ansiblelint.prerun).

Molecule 3.x names the driver "delegated", which is env.sh's default.
A modern molecule (>=6) would use the driver name "default" -- export `PPG_LOCAL_DRIVER=default` before sourcing env.sh -- but that combination is untested here.

Always activate the venv before running molecule so its ansible is used.

## Quick start

On a machine that is both hypervisor and runner:

```
source ~/.venvs/ppg-molecule/bin/activate
cd ppg-testing
. local/env.sh
python3 tools/render.py --group pg_tde/tde
cd pg_tde/tde
export VERSION=ppg-18.4 REPO=testing IO_METHOD=sync
export TDE_REPO=https://github.com/percona/pg_tde.git TDE_BRANCH=release-2.2
molecule test -s debian-13
```

## Remote hypervisor

Set `PPG_HYPERVISOR_SSH=user@host` BEFORE sourcing env.sh.
env.sh derives `LIBVIRT_URI=qemu+ssh://user@host/system` from it and appends a ProxyJump to ANSIBLE_SSH_COMMON_ARGS, because the guests sit on the hypervisor's NAT network and are only reachable through it.
The format must be exactly user@host, typos fail confusingly far downstream (in libvirt connect or ssh, not in env.sh).
PPG_HYPERVISOR_SSH wins over a pre-set LIBVIRT_URI, on purpose.

Sanity check before starting molecule:

```
virsh -c "qemu+ssh://user@host/system" list --all
```

Caveat: re-sourcing env.sh in the same shell appends a duplicate ProxyJump entry.
Use a fresh shell when switching hypervisors.

## Scenario env vars

env.sh only handles the backend.
The scenarios themselves need the same vars CI passes, check the matching job in the jenkins-pipelines repo for your component.

For pg_tde/tde this set is proven green:

```
export VERSION=ppg-18.4
export REPO=testing
export TDE_REPO=https://github.com/percona/pg_tde.git
export TDE_BRANCH=release-2.2
export IO_METHOD=sync
```

Leave MAJOR_REPO unset.
Note: tde.groovy's default TDE_BRANCH=release-2.2.0 is a stale upstream ref, use release-2.2.

## Env var reference

| var | default | meaning |
| --- | --- | --- |
| driver | delegated (from PPG_LOCAL_DRIVER) | backend selection, "default" for molecule >=6 |
| BUILD_NUMBER | local | instance-name suffix. static on purpose, so destroy-by-name works from any shell; override for parallel runs of the same scenario |
| LIBVIRT_URI | qemu:///system | libvirt connection |
| LIBVIRT_POOL | default | storage pool |
| LIBVIRT_NETWORK | default | NAT network |
| PPG_HYPERVISOR_SSH | unset | user@host of a remote hypervisor, derives LIBVIRT_URI and ProxyJump |
| PPG_LOCAL_CPUS | from instance_type | override the instance_type to size mapping |
| PPG_LOCAL_MEMORY | from instance_type | same, memory in MiB |
| PPG_IMAGE_CACHE | ~/.cache/ppg-molecule/images | downloaded vendor images |

## How it works

Scenario dirs (molecule/<os>/molecule.yml) are not in git any more -- they get rendered from each group's scenario.yml plus catalog/ by tools/render.py, and the output carries a "do not edit" header. Use `--all` to render every group, or `--clean` to remove generated files again.
Vendor cloud images are downloaded once, cached under PPG_IMAGE_CACHE, and uploaded to the pool as `base-<image>.qcow2` volumes.
Each instance is a qcow2 overlay on top of that base, sized max(volume_size or 30G, base virtual size) -- OL KVM templates are 37G, going below the base size truncates the disk.
Each instance also gets a cloud-init NoCloud seed iso.
The ssh key is ephemeral, generated per scenario.
The instance user comes from the image catalog in `playbooks/libvirt/images.yml`, NOT from the molecule.yml ssh_user -- that one is AMI-specific.
The backend additionally creates the molecule.yml user via cloud-init, because the shared prepare.yml expects it.
OL images: the catalog URLs are versioned (there is no "latest" symlink), checksums come from the HTML table at https://yum.oracle.com/oracle-linux-templates.html, and the default user is cloud-user (opc is OCI-only).
Ubuntu .img files are qcow2 already, no conversion needed.
debian-13+ images are EFI-only, so the domain template uses EFI for all images.

## Not supported locally

* RHEL -- no subscription, use rocky
* arm64 -- planned separately, the self-hosted CI plan has dedicated arm hardware for it

## Troubleshooting

* crashed create: run `molecule destroy -s <scenario>` first, destroy tolerates partial state.
  Rerunning create against leftovers fails with "already exists".
* stale domain/volumes by hand: `virsh destroy <name>`, `virsh undefine <name> --nvram`, `virsh vol-delete --pool default <name>.qcow2` and `<name>-seed.iso`.
  Never delete `base-*.qcow2`, that is the image cache.
* "hung" prepare/converge: usually no guest egress, see the firewall section above.
* IP wait timeout: the error names the domain, check `virsh domifaddr <name> --source lease` and the serial console via `virsh console <name>`.
* do not run two scenarios sharing the same base image concurrently until base-volume locking exists.
  There is a TOCTOU between the base existence check and the upload, the second run can get a half-uploaded base.
  Different images at the same time are fine.
* failures print censored "no_log" output for some tasks unless MOLECULE_DEBUG=1 is set.
  The backend's own failure-prone tasks are exempted and name the domain.
* checksum mismatch on image download: the vendor rotated the "latest" image. Refresh url and checksum in `playbooks/libvirt/images.yml`.

## task shortcuts

`Taskfile.yml` at the repo root is optional sugar over `tools/run.py`, nothing more -- every task just shells out, so `tools/run.py` works fine standalone without go-task installed.
Each task sources `local/env.sh` itself, so you only need to export `PPG_HYPERVISOR_SSH` (if remote) before calling `task`.

Install go-task if you don't have it:

```
sh -c "$(curl -sL https://taskfile.dev/install.sh)" -- -d -b ~/.local/bin
```

Make sure `~/.local/bin` is on PATH.

Examples:

```
task list                                   # list groups
task list GROUP=pg_tde/tde                  # group's oses/sequences/params
task tde OS=ol-9                            # family shortcut
task pgsm OS=ol-9
task psp OS=ol-9
task ppg SCENARIO=pg-17 OS=ol-9
task run GROUP=pg_tde/tde OS="ol-9 debian-12" -- --param TDE_BRANCH=main --keep
task destroy GROUP=pg_tde/tde OS=ol-9
```

`OS` can list several keys, space separated, run sequentially (same as `--os` on run.py).
Anything after `--` is passed straight through to run.py as extra flags.

Heads up on `pg_tde`: the descriptor default `TDE_BRANCH=release-2.2.0` does not exist upstream (the branch is `release-2.2`, the tag is `release-2.2.1`), so the clone task fails with it.
Override until the descriptor is fixed:

```
task tde OS=ol-9 -- --param TDE_BRANCH=release-2.2
```
By default python comes from `~/.venvs/ppg-molecule/bin/python`, override with `PPG_PY=/path/to/python`.

The `bot-up` / `bot-down` / `bot-logs` tasks manage the local buildbot compose stack at `local/buildbot/docker-compose.yml`.
