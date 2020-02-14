#!/usr/bin/env python3
"""Unit-tests for logrotlib"""

import unittest
from unittest import mock
import io
from pathlib import Path
from tpcrontools.cronctllib import RobotDef, CronLine
from tpcrontools.cronctllib import get_crontab_list, write_new_crontab, get_robot_defs, \
    get_all_robots, remove_paths_from_cron, parse_crontab_list, \
    filter_robots_by_type, get_present_types, list_paths, \
    sort_robots, update_cron_by_robots

class TestCronctllib(unittest.TestCase):
    """Main test class"""

    def test_get_crontab_list(self):
        """Test of function getting user's of crontab"""
        crontab = get_crontab_list(['printf', r'%s\n%s\n', 'fakecron line1', 'fakecron line2'])
        self.assertEqual(crontab, ['fakecron line1', 'fakecron line2'])

    def test_write_new_crontab(self):
        """Test of function setting user's of crontab"""
        result = write_new_crontab(
            ['a', 'b', '', '1', '2', ''],
            [
                'bash',
                '-c',
                """
                trap 'rm -f /tmp/test_data.$$ /tmp/test_except.$$' EXIT
                cat > /tmp/test_data.$$
                printf 'a\nb\n\n1\n2\n' > /tmp/test_except.$$
                cmp /tmp/test_data.$$ /tmp/test_except.$$
                """
            ]
        )
        self.assertTrue(result)

    def test_get_robot_defs_simple(self):
        """Test of getting cron defs from one robot text with simple type"""
        result = get_robot_defs('file', """
#!/usr/bin/env bash
#P:cron:10 10,12,15,17 * * *
#P:cron:59 23 * * *
#T:cron:*/10 * * * *

cd $(dirname $0)

. functions.shl
""")
        self.assertListEqual(result, [
            RobotDef('file', '10 10,12,15,17 * * *', 'P'),
            RobotDef('file', '59 23 * * *', 'P'),
            RobotDef('file', '*/10 * * * *', 'T')
        ])

    def test_get_robot_defs_complex(self):
        """Test of getting cron defs from one robot text with complex type"""
        result = get_robot_defs('file', """
#!/usr/bin/env bash

#PD:cron:30 2 * * *

cd $(dirname $0)
cd ../ao3-statistiky-sh
""")
        self.assertListEqual(result, [
            RobotDef('file', '30 2 * * *', 'PD')
        ])

    def test_get_all_robots_in_file(self):
        """Test loading informations about robots in file"""
        test_path = Path(__file__).parent.joinpath(
            'robot_defs',
            'cron.air_reservation_refresh.sh'
        )
        robots = get_all_robots([test_path, test_path])
        self.assertSetEqual(robots, {
            RobotDef(str(test_path), '10 10,12,15,17 * * *', 'P'),
            RobotDef(str(test_path), '59 23 * * *', 'P'),
            RobotDef(str(test_path), '*/10 * * * *', 'T')
        })
    def test_get_all_robots_in_file_and_folder(self):
        """Test loading informations about robots in folder - especialy duplicities"""
        test_path = Path(__file__).parent.joinpath(
            'robot_defs',
            'cron.air_reservation_refresh.sh'
        )
        tests_path = Path(__file__).parent.joinpath('robot_defs')
        robots = get_all_robots([test_path, tests_path])
        self.assertSetEqual(robots, {
            RobotDef(str(test_path), '10 10,12,15,17 * * *', 'P'),
            RobotDef(str(test_path), '59 23 * * *', 'P'),
            RobotDef(str(test_path), '*/10 * * * *', 'T'),
            RobotDef(str(tests_path)+'/cron.create-reservations-list-csv.sh', '30 2 * * *', 'PD')
        })

    def test_get_present_types(self):
        """ Test of getting unique set of types present in given list"""
        robots = {
            RobotDef('file', '10 10,12,15,17 * * *', 'P'),
            RobotDef('file', '59 23 * * *', 'P'),
            RobotDef('file', '*/10 * * * *', 'T'),
            RobotDef('file', '30 2 * * *', 'PD')
        }
        self.assertSetEqual(get_present_types(robots), {'P', 'T', 'D'})

    def test_filter_robots_by_type(self):
        """Test of filter robot defs by type char"""
        robots = {
            RobotDef('file', '10 10,12,15,17 * * *', 'P'),
            RobotDef('file', '59 23 * * *', 'P'),
            RobotDef('file', '*/10 * * * *', 'T'),
            RobotDef('file', '30 2 * * *', 'PD')
        }
        self.assertSetEqual(set(filter_robots_by_type(robots, 'P')), {
            RobotDef('file', '10 10,12,15,17 * * *', 'P'),
            RobotDef('file', '59 23 * * *', 'P'),
            RobotDef('file', '30 2 * * *', 'PD')
        })

    def test_list_paths(self):
        """Test of list all cron defs from testing robot_defs"""
        with mock.patch('sys.stdout', new=io.StringIO()) as fake_stdout:
            path = Path(__file__).parent.joinpath('robot_defs')
            list_paths([path])
            self.maxDiff = 2048 # pylint: disable=invalid-name
            self.assertMultiLineEqual(fake_stdout.getvalue(), \
"""Jobs for environment P (production):
  {path}/cron.air_reservation_refresh.sh                 10 10,12,15,17 * * *      P
  {path}/cron.air_reservation_refresh.sh                 59 23 * * *               P
  {path}/cron.create-reservations-list-csv.sh            30 2 * * *                PD

Jobs for environment T (test):
  {path}/cron.air_reservation_refresh.sh                 */10 * * * *              T

Jobs for environment D (devel):
  {path}/cron.create-reservations-list-csv.sh            30 2 * * *                PD

""".format(path=path))

    def test_sort_robots(self):
        """Test of sort robot type chars"""
        self.assertListEqual(['P', 'T', 'D', 'I', 'A'], sort_robots(['T', 'D', 'A', 'I', 'P']))

    def test_parse_crontab_list(self):
        """Test of parsing crontab content"""
        crontab = [
            '# Some comment',
            'MAILTO=address@example.com',
            r'* * * * * very\ often\ job',
            "0 15 * * * 'commented job' #Comment",
            '@reboot job started at powerup',
            'a * * * * bad timedef',
            '*/20 1-5,10 * * * very complex timedef',
            ''
        ]
        expected = [
            CronLine(RobotDef('', '', ''), '# Some comment'),
            CronLine(RobotDef('', '', ''), 'MAILTO=address@example.com'),
            CronLine(RobotDef('very often job', '* * * * *', ''), '* * * * * very\\ often\\ job'),
            CronLine(
                RobotDef('commented job', '0 15 * * *', ''),
                "0 15 * * * 'commented job' #Comment"
            ),
            CronLine(RobotDef('job', '@reboot', ''), '@reboot job started at powerup'),
            CronLine(RobotDef('', '', ''), 'a * * * * bad timedef'),
            CronLine(RobotDef('very', '*/20 1-5,10 * * *', ''), '*/20 1-5,10 * * * very complex timedef'),
            CronLine(RobotDef('', '', ''), '')
        ]
        self.maxDiff = None # pylint: disable=invalid-name
        with self.assertLogs() as logs_catcher:
            self.assertListEqual(parse_crontab_list(crontab), expected)
        self.assertListEqual(
            logs_catcher.output,
            ['ERROR:root:Unknown cron line format: "a * * * * bad timedef"']
        )

    def test_remove_paths_from_cron(self):
        """Test of filtering out paths from crontab"""
        crontab = [
            '# Some comment',
            'MAILTO=address@example.com',
            '* * * * * /removed/path/something',
            "* * * * * '/removed/path/something else'",
            "* * * * * '/removed/path not/something else'",
            '* * * * * /non/removed/path/something',
            ''
        ]
        expected = [
            '# Some comment',
            'MAILTO=address@example.com',
            "* * * * * '/removed/path not/something else'",
            '* * * * * /non/removed/path/something',
            ''
        ]
        self.assertListEqual(remove_paths_from_cron(crontab, [Path('/removed/path')]), expected)

    def test_update_cron_by_robots(self):
        """Test of updating list of CronLine by list of RobotDef"""
        crontab = parse_crontab_list([
            '# Some comment',
            'MAILTO=address@example.com',
            '* * * * * /removed/path/something',
            '* * * * * /modified/path/something',
            '1 2 3 4 5 /unchanged/path/something'
        ])
        robots = [
            RobotDef('/unchanged/path/something', '1 2 3 4 5', 'I'),
            RobotDef('/modified/path/something', '6 7 8 9 7', 'I'),
            RobotDef('/added/path/something', '* * * * *', 'I'),
        ]
        paths = [
            Path('/removed/'),
            Path('/modified'),
            Path('/unchanged')
        ]
        expected = [
            '# Some comment',
            'MAILTO=address@example.com',
            '1 2 3 4 5 /unchanged/path/something',
            '* * * * * /added/path/something',
            '6 7 8 9 7 /modified/path/something',
        ]
        self.maxDiff = None # pylint: disable=invalid-name
        self.assertListEqual(update_cron_by_robots(crontab, robots, paths), expected)
