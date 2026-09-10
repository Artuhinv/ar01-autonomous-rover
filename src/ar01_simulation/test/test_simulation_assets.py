from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
import yaml


PACKAGE_DIR = Path(__file__).parents[1]


def test_p0_room_contains_floor_walls_and_obstacles():
    root = ET.parse(PACKAGE_DIR / 'worlds' / 'p0_room.sdf').getroot()
    world = root.find("world[@name='p0_room']")
    assert world is not None

    models = {model.attrib['name'] for model in world.findall('model')}
    assert models == {
        'floor',
        'wall_north',
        'wall_south',
        'wall_east',
        'wall_west',
        'box_1',
        'box_2',
        'box_3',
    }
    for model in world.findall('model'):
        assert model.findtext('static') == 'true'
        link = model.find('link')
        assert link.find('visual') is not None
        assert link.find('collision') is not None


def test_diff_drive_controller_matches_mechanical_contract():
    with (PACKAGE_DIR / 'config' / 'controllers.yaml').open() as config_file:
        config = yaml.safe_load(config_file)

    manager = config['controller_manager']['ros__parameters']
    assert manager['joint_state_broadcaster']['type'] == (
        'joint_state_broadcaster/JointStateBroadcaster'
    )
    assert manager['diff_drive_controller']['type'] == (
        'diff_drive_controller/DiffDriveController'
    )

    drive = config['diff_drive_controller']['ros__parameters']
    assert drive['left_wheel_names'] == ['left_wheel_joint']
    assert drive['right_wheel_names'] == ['right_wheel_joint']
    assert drive['wheel_separation'] == pytest.approx(0.310)
    assert drive['wheel_radius'] == pytest.approx(0.050)
    assert drive['position_feedback'] is True
    assert drive['open_loop'] is False
