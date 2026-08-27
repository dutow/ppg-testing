import re

from tools import catalog

VARS_DIR = "/storage/pgqa/jenkins-pipelines/vars"
ENVPPG = VARS_DIR + "/moleculeEnvPPG.groovy"

LIST_FILES = {
    "all": "ppgOperatingSystemsALL.groovy",
    "amd": "ppgOperatingSystemsAMD.groovy",
    "arm": "ppgOperatingSystemsARM.groovy",
    "ssl1": "ppgOperatingSystemsSSL1.groovy",
    "ssl3": "ppgOperatingSystemsSSL3.groovy",
    "ssl35": "ppgOperatingSystemsSSL35.groovy",
    "performance": "ppgOperatingSystemsPerformance.groovy",
}


def test_lists_match_jenkins():
    lists = catalog.load("os-lists.yml")
    for name, fname in LIST_FILES.items():
        groovy = open(VARS_DIR + "/" + fname).read()
        jenkins_oses = re.findall(r"'([a-z0-9-]+)'", groovy)
        assert lists[name] == jenkins_oses, name


def test_amis_match_moleculeenv():
    envtext = open(ENVPPG).read()
    amis = dict(re.findall(r"export ami_(\w+)=(ami-\w+)", envtext))
    oses = catalog.load("os.yml")
    for os_name, e in oses.items():
        assert e["aws"]["ami_x86"] == amis[e["ami_var"] + "_x86_64"], os_name
        assert e["aws"]["ami_arm"] == amis[e["ami_var"] + "_arm64"], os_name
    assert len(amis) == 2 * len(oses)


def test_arm_entry():
    e = catalog.os_entry("debian-13-arm")
    assert e["arm"] and e["base"] == "debian-13"
    assert e["aws"]["ami_arm"] == "ami-009aa536d30f23947"


def test_subnets_match():
    envtext = open(ENVPPG).read()
    subs = dict(re.findall(r"export vpc_subnet_id_(\w+)=(subnet-\w+)", envtext))
    assert catalog.load("aws.yml")["subnets"] == subs


def test_lists_reference_known_os_keys():
    bases = {k[:-4] if k.endswith("-arm") else k for k in catalog.load("os-lists.yml")["all"]}
    assert bases == set(catalog.load("os.yml"))


def test_os_entry_fields_sane():
    for os_name, e in catalog.load("os.yml").items():
        assert e["family"] in ("deb", "rpm"), os_name
        assert e["aws"]["ssh_user"], os_name
        assert e["aws"]["root_device"], os_name
