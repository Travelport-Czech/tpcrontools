#!/usr/bin/env python3
"""Unit-tested functions for cronctl"""

from collections import namedtuple
import subprocess
import re
import logging
import shlex
from pathlib import Path
import difflib

ROBOT_DEF_REGEX = re.compile(r'^(#|//)(?P<type>[A-Z]*):cron:(?P<def>.*)$', re.MULTILINE)
CRON_DEF_REGEX = re.compile(r"""
        ^(
        [#].*                                       # comment
        |\S+=.*                                     # var assign
        |(?P<time1>@\S+)\s+(?P<cmd1>\S.*)           # time spec shortcut ie @reboot
        |(?P<time2>([-0-9/*,]+\s+){5})(?P<cmd2>\S.*) # common format
        |\s*                                        # empty line
        )$
""", re.VERBOSE)
TYPE_CHARS_DESCRIPTION = {
        'P': 'production',
        'D': 'devel',
        'T': 'test',
        'S': 'support',
        'I': 'internal',
        'R': 'robots'
}
TYPE_CHARS_ORDER = 'PRTDSI'

RobotDef = namedtuple('RobotDef', ('fullname', 'cron_def', 'type_chars'))
CronLine = namedtuple('CronLine', ('robot_def', 'text'))

def list_paths(paths):
    """List all robots sorted by type"""
    abs_paths = to_abs_paths(paths)
    robots = get_all_robots(abs_paths)
    present_types = sort_robots(get_present_types(robots))
    list_robots(robots, present_types)

def sort_robots(robot_types):
    """Sort robot type chars by TYPE_CHARS_ORDER"""
    return sorted(robot_types, key=get_sort_robots_weight)

def get_sort_robots_weight(robot_type):
    """Calculate robot type weight for sorting"""
    weight = TYPE_CHARS_ORDER.find(robot_type)
    return weight if weight > -1 else len(TYPE_CHARS_ORDER)

def list_robots(robots, present_types):
    """Print given robots grouped by types"""
    for type_char in present_types:
        print('Jobs for environment {type_char} ({type_description}):'.format(
            type_char=type_char,
            type_description=TYPE_CHARS_DESCRIPTION.get(type_char, '')
        ))
        for robot in sorted(filter_robots_by_type(robots, type_char)):
            print('  {r.fullname:<90} {r.cron_def:<25} {r.type_chars}'.format(r=robot))
        print()
    return True


def add_paths(paths, type_char, force):
    """Check paths for new robots and update user's crontab"""
    abs_paths = to_abs_paths(paths)
    robots = filter_robots_by_type(get_all_robots(abs_paths), type_char)
    old_crontab = get_crontab_list()
    crontab = parse_crontab_list(old_crontab)
    new_crontab = update_cron_by_robots(crontab, robots, abs_paths)
    return save_changes(old_crontab, new_crontab, force)

def remove_paths(paths, force):
    """Remove all crontab lines containing given paths"""
    abs_paths = to_abs_paths(paths)
    old_crontab = get_crontab_list()
    new_crontab = remove_paths_from_cron(old_crontab, abs_paths)
    return save_changes(old_crontab, new_crontab, force)

def save_changes(old_crontab, new_crontab, force):
    """If any diff, show them and save to file"""
    if old_crontab == new_crontab:
        print('No crontab changes.')
    else:
        print_diff(old_crontab, new_crontab)
        if force or confirm_write():
            if write_new_crontab(new_crontab):
                print('New crontab successfully written.')
            else:
                print('An error occurred while writing new crontab.')
                return False
    return True

def to_abs_paths(paths):
    """Convert list of paths to absolute"""
    return [Path(path).resolve() for path in paths]

def update_cron_by_robots(crontab, robots, paths):
    """Update list of CronLine by list of RobotDef"""
    output_cron = []
    robots_set = {
        RobotDef(robot.fullname, robot.cron_def, '')
        for robot in robots
    }
    cron_robots = {
        RobotDef(cron.robot_def.fullname, cron.robot_def.cron_def, '')
        for cron in crontab
    }
    paths_parts = [path.parts for path in paths]
    output_cron = [
        cron.text
        for cron in crontab
        if cron.robot_def in robots_set or not_in_paths(cron.robot_def.fullname, paths_parts)
    ] + sorted([
        robot.cron_def + ' ' + robot.fullname
        for robot in robots_set if robot not in cron_robots
    ])
    return output_cron

def not_in_paths(fullname, paths_parts):
    """Check if file is in any of paths or subdir"""
    fullname_parts = Path(fullname).parts
    for path in paths_parts:
        if fullname_parts[:len(path)] == path:
            return False
    return True

def confirm_write():
    """Asks the user if agrees to write changes"""
    print()
    answer = ''
    while answer not in ('a', 'y', 'j', 'n'):
        answer = input('Really write changes (y/n)? ').lower().strip()
    return answer != 'n'

def print_diff(old_crontab, new_crontab):
    """Print diff between lists"""
    print('The required crontab changes are:')
    diff = difflib.Differ().compare(old_crontab, new_crontab)
    print('\n'.join(diff))

def remove_paths_from_cron(crontab_list, paths):
    """Remove all crontab lines containing given paths"""
    parsed_cron = parse_crontab_list(crontab_list)
    paths_parts = [path.parts for path in paths]
    output_cron = [
        line.text
        for line in parsed_cron
        if not_in_paths(line.robot_def.fullname, paths_parts)
    ]
    return output_cron

def parse_crontab_list(crontab_list):
    """Parse crontab content line by line"""
    cron_lines = []
    for line in crontab_list:
        m_line = CRON_DEF_REGEX.match(line)
        if m_line:
            command = (m_line.group('cmd1') or m_line.group('cmd2') or '').strip()
            if command:
                command = shlex.split(command)[0]
            robot_def = RobotDef(
                command,
                (m_line.group('time1') or m_line.group('time2') or '').strip(),
                ''
            )
        else:
            logging.error('Unknown cron line format: "%s"', line)
            robot_def = RobotDef('', '', '')
        cron_lines.append(CronLine(robot_def, line))
    return cron_lines

def get_crontab_list(cmd=('crontab', '-l')):
    """Get list of current user's crontab definitions"""
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        universal_newlines=True,
        check=False
    )
    return result.stdout.rstrip().split('\n')

def write_new_crontab(records, cmd=('crontab', '-')):
    """Overwrite user's crontab with given records"""
    cron_text = '\n'.join(records).rstrip() + '\n'
    result = subprocess.run(
        cmd,
        input=cron_text,
        universal_newlines=True,
        check=False
    )
    return result.returncode == 0

def get_all_robots(paths):
    """Get all robots def from all paths"""
    defs = []
    for path in paths:
        if path.is_dir():
            for fullname in path.iterdir():
                if fullname.is_file():
                    defs += get_robot_defs_from_file(fullname)
        elif path.is_file():
            defs += get_robot_defs_from_file(path)
    return set(defs)

def get_robot_defs_from_file(fullname):
    """Get robot defs by filename"""
    with fullname.open() as fin:
        return get_robot_defs(fullname, fin.read())

def get_robot_defs(fullname, source):
    """Scan given source for cron definitions with type"""
    return [RobotDef(str(fullname), match.group('def').strip(), match.group('type'))
            for match in ROBOT_DEF_REGEX.finditer(source)]

def filter_robots_by_type(robots, type_char):
    """Filter robot defs by type char"""
    return (robot for robot in robots if type_char in robot.type_chars)

def get_present_types(robots):
    """Get unique set of types present in given list"""
    return {type_char for robot in robots for type_char in robot.type_chars}
