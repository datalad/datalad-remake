

from argparse import ArgumentParser


argument_parser = ArgumentParser()
argument_parser.add_argument('source', help='Source URL')
argument_parser.add_argument('-v', '--version', help='Version of the source (sha or tag)')
argument_parser.add_argument('-p', '--pattern', help='File pattern of files that should be provisioned')


def main():
    arguments = argument_parser.parse_args()




if __name__ == '__main__':
    main()
