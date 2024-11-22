import pytest
from annexremote import Master
from datalad_core.config import ConfigItem
from datalad_core.tests.fixtures import cfgman  # noqa: F401
from datalad_next.tests import skip_if_on_windows

from datalad_remake import (
    priority_config_key,
    specification_dir,
    template_dir,
)
from datalad_remake.annexremotes.remake_remote import RemakeRemote
from datalad_remake.commands.make_cmd import build_json
from datalad_remake.commands.tests.create_datasets import create_ds_hierarchy

from .utils import run_remake_remote

# The following templates create differing content if formatted with different
# values for `label`. This is intended here, it
# only works because we drive the special remote ourselves, and skip the
# content validation. So they are not a valid example for different compute
# instructions that lead to identical results, but just a way to test the
# priority code.
template = """
parameters = ['content']
command = ["bash", "-c", "echo from {label}: {{content}} > 'a.txt'"]
"""


@skip_if_on_windows
@pytest.mark.parametrize('priority', [['alpha', 'beta'], ['beta', 'alpha']])
def test_compute_remote_priority(tmp_path, cfgman, monkeypatch, priority):  # noqa: F811
    dataset = create_ds_hierarchy(
        tmp_path=tmp_path,
        name='ds1',
        subdataset_levels=0,
        signing_key=None,
    )[0][2]

    monkeypatch.chdir(dataset.path)

    template_path = dataset.pathobj / template_dir
    template_path.mkdir(parents=True)
    for label in priority:
        (template_path / label).write_text(template.format(label=label))
    dataset.save()

    specification_path = dataset.pathobj / specification_dir
    for label in ('alpha', 'beta'):
        specification_path.mkdir(parents=True, exist_ok=True)
        (specification_path / f'00000-{label}').write_text(
            build_json(
                label,
                [],
                ['a.txt'],
                {'content': f'{label}_parameter'},
            )
        )
    dataset.save()

    # The compute instruction URLs that are associated with `a.txt`. The order
    # in which the URLs are reported to the special remote is fixed: first
    # `alpha`, second `beta`.
    urls = [
        'datalad-make:///?'
        + '&'.join(
            [
                f'label={label}',
                f'root_version={dataset.repo.get_hexsha()}',
                f'specification=00000-{label}',
                'this=a.txt',
            ]
        )
        for label in ['alpha', 'beta']
    ]

    # Run the special remote with the given priority configuration.
    with cfgman.overrides({priority_config_key: ConfigItem(','.join(priority))}):
        run_remake_remote(tmp_path, urls)

    # At this point the datalad-remake remote should have executed the
    # prioritized template and written the result.
    assert (
        tmp_path / 'remade.txt'
    ).read_text().strip() == f'from {priority[0]}: {priority[0]}_parameter'


def test_config_precedence(existing_dataset, tmp_path, cfgman, monkeypatch):  # noqa: F811
    existing_dataset.config.add('datalad.make.priority', '1', scope='branch')

    monkeypatch.setattr(
        RemakeRemote, '_get_dataset_dir', lambda _: existing_dataset.pathobj
    )
    remake_remote = RemakeRemote(Master())

    # The lowest priority info should be read from the `.datalad/config`-file
    # of the dataset.
    assert remake_remote._get_priorities() == ['1']  # noqa SLF001

    global_config_file = tmp_path / 'config'
    monkeypatch.setenv('GIT_CONFIG_GLOBAL', str(global_config_file))

    # Global git config should overwrite the dataset config.
    global_config_file.write_text('[datalad "make"]\n    priority = 2\n')
    global_config_source = remake_remote.config_manager.sources['git-global']
    global_config_source.load()
    assert remake_remote._get_priorities() == ['2']  # noqa SLF001

    # Local git config should overwrite global git config and dataset config.
    existing_dataset.config.add('datalad.make.priority', '3', scope='local')
    git_source = remake_remote.config_manager.sources['git']
    git_source.load()
    assert remake_remote._get_priorities() == ['3']  # noqa SLF001

    # Git command configurations, i.e. environment variables, should overwrite
    # local git config.
    existing_dataset.config.add('datalad.make.priority', '3', scope='local')
    git_source = remake_remote.config_manager.sources['git']
    git_source.load()
    with cfgman.overrides({priority_config_key: ConfigItem('4')}):
        assert remake_remote._get_priorities() == ['4']  # noqa SLF001
