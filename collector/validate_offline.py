import json,sys
from pathlib import Path
def main():
 assert len(json.load(open('collector/fixtures/qa-scenarios.json'))['scenarios'])>=25
 assert len(json.load(open('config/sources/source-registry.json')))==62
 print('VALIDATOR_STATUS=PASS')
if __name__=='__main__':main()
