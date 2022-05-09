#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
Een kleine analyse van erfgoed uit de inventaris naar beschermingsstatuut.
'''

from skosprovider_atramhasis.providers import AtramhasisProvider
from skosprovider.providers import DictionaryProvider
from skosprovider.utils import dict_dumper

import requests

import csv
import os

from datetime import datetime

from utils import fetch_query
from utils import get_erfgoedtypes
from utils import get_erfgoedobject
from utils import analyseer_aanduidingen
from utils import analyseer_kenmerkgroepen
from utils import analyseer_relaties
from utils import clean_relaties

# Alle disciplines
DISCIPLINE = None
# Alles behalve varend
#DISCIPLINE = [1,2,3]
# Enkel bouwkundig
#DISCIPLINE = [2]

# Alles ongeacht erfgoedwaarde
ERFGOEDWAARDE = None
#Alles met erfgoedwaarde
#ERFGOEDWAARDE = True
#Alles zonder erfgoedwaarde
#ERFGOEDWAARDE = False

# Alles ongeacht de rechtsgevolgen
# RECHTSGEVOLGEN = None
# Alles wat beschermd is
RECHTSGEVOLGEN = 'beschermd'

# Alles ongeacht type
# Opgelet, niet gebruiken zonder combinatie met andere parameters.
# Dit is een zeer zware vraag die uren werk kan vragen
#CONCEPT = None
# kerken
#CONCEPT = 1005
# katholieke kerken
#CONCEPT = 230
# begijnhoven
CONCEPT = 53
# eet- en drinkgelegenheden
#CONCEPT = 881
# windmolens
#CONCEPT = 514
# hondenhokken
#CONCEPT = 192
# lagere scholen
#CONCEPT = 259

# NOT niets, alles dus
NOT_CONCEPT = []
# NOT abdijkerken, begijnhofkerken, kloosterkerken
#NOT_CONCEPT = [6, 52, 242]

# URLs
INVENTARIS_HOST = 'https://inventaris.onroerenderfgoed.be/'
URL_ERFGOEDOBJECTEN = INVENTARIS_HOST + 'erfgoedobjecten'

os.makedirs(f'./output', exist_ok=True)

FILENAME_LOG = './output/query_%s.log' % datetime.now()

import logging
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filename=FILENAME_LOG,
    filemode='w',
    level=logging.INFO
)

def generate_csv(
        discipline = None, erfgoedwaarde = None,
        rechtsgevolgen = None,
        concept = None, not_concept = []
    ):

    session = requests.Session()

    query = {}

    if discipline:
        query['discipline']: '[%s]' % (','.join([str(d) for d in discipline]))
    if erfgoedwaarde:
        query['erfgoedwaarde'] = erfgoedwaarde
    if concept:
        query['typologie'] = [concept.id]
        not_concept = [f'-%s{nc}' for nc.id in not_concept]
        query['typologie'].extend(not_concept)
    if rechtsgevolgen:
        query['rechtsgevolgen'] = rechtsgevolgen

    logging.info('Uit te voeren query: %s', query)

    erfgoedobjecten = fetch_query(
        URL_ERFGOEDOBJECTEN,
        query,
        session=session
    )

    export = []
    for e in erfgoedobjecten:
        logging.info('Opvragen %s met self %s', e['uri'], e['self'])
        exp = {
            'id': e['id'],
            'uri': e['uri'],
            'self': e['self'],
            'naam': e['naam'],
            'omvang': e['omvang']['naam'],
            'disciplines': "".join([d['naam'][0] for d in e['disciplines']]),
            'locatie_samenvatting': e['locatie_samenvatting'],
            'provincie': e['locatie']['provincie'],
            'gemeente': e['locatie']['gemeente'],
            'deelgemeente': e['locatie']['deelgemeente'],
            'straat': e['locatie']['straat']
        }
        extra_e = get_erfgoedobject(e['self'], session=session)
        exp.update({
            'erfgoedwaarde': 'ja' if extra_e['erfgoedwaarde'] else 'nee',
            'fysieke staat': extra_e['locatie']['status']['naam']
        })
        exp.update(analyseer_aanduidingen(extra_e))
        exp.update(analyseer_kenmerkgroepen(extra_e, concept))
        exp.update(analyseer_relaties(extra_e))
        export.append(exp)

    export = clean_relaties(export)
    if concept:
        filename = './output/query_%s_%s_%s.csv' % (concept.id, concept.label('nl-BE').label, datetime.now())
    else:
        filename = './output/query_%s.csv' % datetime.now()
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = [
            'id', 'uri', 'self', 'naam',
            'omvang', 'disciplines',
            'erfgoedwaarde', 'fysieke staat',
            'locatie_samenvatting', 'provincie', 'gemeente',
            'deelgemeente', 'straat',
            'omvat', 'deel van',
            'aangeduid', 'vastgesteld', 'beschermd', 'erfgoedlandschap', 'unesco',
            'monument', 'enkel monument',
            'sdgezicht', 'enkel sdgezicht',
            'landschap', 'enkel landschap',
            'site', 'overgangszone',
            'ongeldige beschermingen',
            'typologie', 'datering', 'stijl',
            'primaire kenmerkgroepen'
        ]
        writer = csv.DictWriter(
            csvfile,
            fieldnames=fieldnames
        )

        writer.writeheader()
        for e in export:
            writer.writerow(e)

def main():

    if CONCEPT:
        logging.info(f'Ophalen van Concept {CONCEPT}')
        erfgoedtypes = get_erfgoedtypes()
        concept = erfgoedtypes.get_by_id(CONCEPT)

        not_concept = []

        for c in NOT_CONCEPT:
            not_concept.append(get_erfgoedtypes().get_by_id(c))

        tpl = 'Concept: %s (%s)'
        logging.info(tpl % (concept.label().label, concept.uri))

        tpl = 'Maar niet concept: %s (%s)'
        for c in not_concept:
            logging.info(tpl % (c.label().label, c.uri))
    else:
        concept = None
        not_concept = []

    logging.info(f'Start genereren CSV')
    generate_csv(
        DISCIPLINE, ERFGOEDWAARDE,
        RECHTSGEVOLGEN,
        concept, not_concept
    )

if __name__ == "__main__":
    main()
