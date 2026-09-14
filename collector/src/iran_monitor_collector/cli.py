import argparse
p=argparse.ArgumentParser(); p.add_argument('command'); p.add_argument('--fixtures-only',action='store_true'); a=p.parse_args(); print('OFFLINE_OK')
