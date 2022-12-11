import argparse
from typing import Any, List

from pylnk3.helpers import for_file, parse


def get_prop(obj: Any, prop_queue: List[str]) -> Any:
    attr = getattr(obj, prop_queue[0])
    if len(prop_queue) > 1:
        return get_prop(attr, prop_queue[1:])
    return attr


HELP = '''
Tool for read or create .lnk files

usage: pylnk3.py [p]arse / [c]reate ...

Examples:
pylnk3 p filename.lnk
pylnk3 c c:\\prog.exe shortcut.lnk
pylnk3 c \\\\192.168.1.1\\share\\file.doc doc.lnk
pylnk3 create c:\\1.txt text.lnk -m Minimized -d "Description"

for more info use help for each action (ex.: "pylnk3 create -h")
'''


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False, prog='pylnk3')
    subparsers = parser.add_subparsers(dest='action', metavar='{p, c, d}')
    parser.add_argument('--help', '-h', action='store_true')

    parser_parse = subparsers.add_parser('parse', aliases=['p'], help='read lnk file')
    parser_parse.add_argument('filename', help='lnk filename to read')
    parser_parse.add_argument('props', nargs='*', help='props path to read')

    parser_create = subparsers.add_parser('create', aliases=['c'], help='create new lnk file')
    parser_create.add_argument('target', help='target path')
    parser_create.add_argument('name', help='lnk filename to create')
    parser_create.add_argument('--arguments', '-a', nargs='?', help='additional arguments')
    parser_create.add_argument('--description', '-d', nargs='?', help='description')
    parser_create.add_argument('--icon', '-i', nargs='?', help='icon filename')
    parser_create.add_argument('--icon-index', '-ii', type=int, default=0, nargs='?', help='icon index')
    parser_create.add_argument('--workdir', '-w', nargs='?', help='working directory')
    parser_create.add_argument('--mode', '-m', nargs='?', choices=['Maximized', 'Normal', 'Minimized'], help='window mode')
    parser_create.add_argument('--file', action='store_true', help='threat target as file (by default guessed by dot in target)')
    parser_create.add_argument(
        '--directory', action='store_true', help='threat target as directory (by default guessed by dot in target)',
    )

    parser_dup = subparsers.add_parser('duplicate', aliases=['d'], help='read and write lnk file')
    parser_dup.add_argument('filename', help='lnk filename to read')
    parser_dup.add_argument('new_filename', help='new filename to write')

    args = parser.parse_args()
    if args.help or not args.action:
        print(HELP.strip())
        exit(1)

    if args.action in ('create', 'c'):
        is_file = None
        if args.file:
            is_file = True
        elif args.directory:
            is_file = False
        for_file(
            args.target, args.name, arguments=args.arguments,
            description=args.description, icon_file=args.icon,
            icon_index=args.icon_index, work_dir=args.workdir,
            window_mode=args.mode,
            is_file=is_file,
        )
    elif args.action in ('parse', 'p'):
        lnk = parse(args.filename)
        props = args.props
        if len(props) == 0:
            print(lnk)
        else:
            for prop in props:
                print(get_prop(lnk, prop.split('.')))
    elif args.action in ('d', 'duplicate'):
        lnk = parse(args.filename)
        new_filename = args.new_filename
        print(lnk)
        lnk.save(new_filename)
        print('saved')
