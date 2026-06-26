from unittest.mock import MagicMock

from ajustes.core.ssh_bridge import SshBridge


def _fake_run(agent_out, fpr_by_pub):
    calls = []

    def run(args):
        calls.append(args)
        if args[:2] == ["ssh-add", "-l"]:
            return MagicMock(returncode=0, stdout=agent_out)
        if args[0] == "ssh-keygen":
            pub = args[-1]
            return MagicMock(returncode=0, stdout=fpr_by_pub.get(pub, ""))
        return MagicMock(returncode=0, stdout="")

    return run, calls


def test_list_keys_reads_fingerprint_and_loaded(tmp_path):
    (tmp_path / "id_ed25519").write_text("P", encoding="utf-8")
    (tmp_path / "id_ed25519.pub").write_text("ssh-ed25519 AAA c", encoding="utf-8")
    pub = str(tmp_path / "id_ed25519.pub")
    run, _ = _fake_run(
        agent_out="256 SHA256:LOADED c (ED25519)\n",
        fpr_by_pub={pub: "256 SHA256:LOADED c (ED25519)"},
    )
    keys = SshBridge(run=run, ssh_dir=tmp_path).list_keys()
    assert len(keys) == 1
    assert keys[0].fingerprint == "SHA256:LOADED"
    assert keys[0].type == "ED25519"
    assert keys[0].loaded is True


def test_list_keys_not_loaded(tmp_path):
    (tmp_path / "k").write_text("P", encoding="utf-8")
    (tmp_path / "k.pub").write_text("x", encoding="utf-8")
    pub = str(tmp_path / "k.pub")
    run, _ = _fake_run(agent_out="The agent has no identities.",
                       fpr_by_pub={pub: "256 SHA256:NOTLOADED c (ED25519)"})
    assert SshBridge(run=run, ssh_dir=tmp_path).list_keys()[0].loaded is False


def test_add_to_agent_command(tmp_path):
    run, calls = _fake_run("", {})
    SshBridge(run=run, ssh_dir=tmp_path).add_to_agent("/home/u/.ssh/id_ed25519")
    assert ["ssh-add", "/home/u/.ssh/id_ed25519"] in calls


def test_remove_from_agent_command(tmp_path):
    run, calls = _fake_run("", {})
    SshBridge(run=run, ssh_dir=tmp_path).remove_from_agent("/home/u/.ssh/id_ed25519")
    assert ["ssh-add", "-d", "/home/u/.ssh/id_ed25519"] in calls
