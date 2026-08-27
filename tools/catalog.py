import pathlib
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent

DEFAULT_CONVERGE = "../../playbooks/playbook.yml"
DEFAULT_BILLING_TAG = "jenkins-pg-molecule"


def load(name):
    with open(ROOT / "catalog" / name) as f:
        return yaml.safe_load(f)


def os_entry(os_key):
    if os_key.endswith("-arm"):
        base, arm = os_key[:-4], True
    else:
        base, arm = os_key, False
    entry = dict(load("os.yml")[base])
    entry["key"] = os_key
    entry["base"] = base
    entry["arm"] = arm
    return entry
