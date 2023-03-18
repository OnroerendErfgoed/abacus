#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
Nuttige functie die helpen erfgoed in de inventaris tellen.
'''

from datetime import datetime

from skosprovider_atramhasis.providers import AtramhasisProvider
from skosprovider.providers import DictionaryProvider
from skosprovider.utils import dict_dumper

import requests

from requests import RequestException

import logging

from dogpile.cache import make_region

def fetch_query(url, parameters, SSO = None, session=None):
    '''
    Fetch all data from a url until there are no more `next` urls in the Link
    header.

    :param str url: The url to fetch from
    :param dict parameters: A dict of query string parameters
    :param str SSO: OpenAM SSO token
    :rtype: dict
    '''

    if not session:
        session = requests.Session()

    data = []

    headers = {'Accept': 'application/json'}
    if SSO:
        headers['OpenAmSSOID'] = SSO

    logging.info('Opzoeken %s met %s', url, parameters)

    res = session.get(url, params=parameters, headers=headers)
    res.raise_for_status()

    aantal = None
    if res.status_code == requests.codes.ok:
        if 'Content-Range' in res.headers:
            aantal = res.headers['Content-Range'].split('/')[-1]
        else:
            aantal = 0
    logging.info('Aantal resultaten: %s', aantal)

    if not aantal:
        return []
    else:
        data.extend(res.json())

    while 'next' in res.links:
        url = res.links['next']['url']
        logging.info('Opzoeken %s', url)
        res = session.get(url, headers=headers)

        data.extend(res.json())

    for d in data:
        # Fix for a weird bug that occasionally happened
        d['self'] = d['uri'].replace('id.erfgoed.net', 'inventaris.onroerenderfgoed.be')

    return data

def _get_url(url, cache, SSO=None, session=None):

    logging.info('Opzoeken %s', url)

    if not session:
        session = requests.Session()

    def creator():
        headers = {'Accept': 'application/json'}
        if SSO:
            headers['OpenAmSSOID'] = SSO

        for i in range(5):  # Try up to 5 times to get the URI
            # Retry scenarios are: connection errors, timeouts, 5xx status codes
            try:
                response = session.get(url, headers=headers, timeout=10)
                if response.ok:
                    return response.json()
                if response.status_code == 404:
                #if 400 <= response.status_code < 500:
                    logging.warning(
                        f"{url} werd niet gevonden: "
                        f"{response.status_code} - {response.text}"
                    )
                    return False
                else:
                    logging.error(
                        f"Probleem ophalen {url}: "
                        f"{response.status_code} - {response.text}"
                    )
            except RequestException as e:
                logging.error(
                    f"Probleem ophalen {url}: {e}"
                )
        else:  # When the loop exited without a break, all retries used.
            raise Exception(f'Ik heb 5 keer geprobeerd {url} te bereiken, maar dit is niet gelukt')

    return cache.get_or_create(url, creator)

erfgoedobjecten_region = make_region().configure(
    'dogpile.cache.dbm',
    expiration_time = 60 * 60 * 24,
    arguments = {
        'filename': './erfgoedobjecten.dbm'
    }
)

def get_erfgoedobject(url, SSO = None, session = None):

    return _get_url(url, erfgoedobjecten_region, SSO, session)

erfgoedtypes = None

def get_erfgoedtypes():
    global erfgoedtypes
    if erfgoedtypes is not None:
        return erfgoedtypes
    # Keep cache in between runs of the script
    # Value is considered valid for 1 week
    erfgoedtypes = AtramhasisProvider(
        {'id': 'vioe-erfgoedtypes)'},
        base_url='https://thesaurus.onroerenderfgoed.be',
        scheme_id='ERFGOEDTYPES',
        cache_config={
            'cache.backend': 'dogpile.cache.dbm',
            'cache.expiration_time': 60 * 60 * 24 * 7,
            'cache.arguments.filename': 'erfgoedtypes.dbm'
        }
    )

    return erfgoedtypes

def is_geldig(aanduiding):
    '''
    Is een aanduidingsobject geldig of niet?
    '''
    nu = datetime.now()
    return datetime.strptime(aanduiding['geldigheid_start'], '%d-%m-%Y') <= nu \
        and (not 'geldigheid_einde' in aanduiding \
        or datetime.strptime(aanduiding['geldigheid_einde'], '%d-%m-%Y') > nu ) \

def analyseer_aanduidingen(erfgoedobject):
    '''
    Analyseer de relaties met aanduidingsobjecten om de beschermingstoestand
    van een erfgoedobject te bepalen.
    '''
    aanduidingen = [a for a in erfgoedobject['relaties'] if a['verwant']['id'] == 5 and is_geldig(a)]

    ret = {
        'aangeduid': len([a for a in aanduidingen if is_geldig(a)]),
        'beschermd': len([a for a in aanduidingen if a['bescherming']]),
        'vastgesteld': len([a for a in aanduidingen if a['vaststelling']]),
        'erfgoedlandschap': len([a for a in aanduidingen if a['aanduidingsobjecttype'] in
            ['Erfgoedlandschap']]),
        'unesco': len([a for a in aanduidingen if a['aanduidingsobjecttype'] in
            ['Unesco werelderfgoed kernzone', 'Unesco werelderfgoed bufferzone']]),
        'monument': len([a for a in aanduidingen if a['aanduidingsobjecttype'] in
            ['Beschermd monument']]),
        'sdgezicht': len([a for a in aanduidingen if a['aanduidingsobjecttype'] in
            ['Beschermd stads- of dorpsgezicht', 'Beschermd stads- of dorpsgezicht, intrinsiek', 'Beschermd stads- of dorpsgezicht, ondersteunend']]),
        'landschap': len([a for a in aanduidingen if a['aanduidingsobjecttype'] in
            ['Beschermd cultuurhistorisch landschap']]),
        'site': len([a for a in aanduidingen if a['aanduidingsobjecttype'] in
            ['Beschermde archeologische site']]),
        'overgangszone': len([a for a in aanduidingen if a['aanduidingsobjecttype'] in
            ['Overgangszone']]),
        'ongeldige beschermingen': len([a for a in erfgoedobject['relaties'] if
            a['verwant']['id'] == 5 and a['bescherming'] and not is_geldig(a)])
    }
    ret['enkel monument'] = 'ja' if \
        ret['monument'] > 0 and \
        ret ['sdgezicht'] == 0 and \
        ret['landschap'] == 0 else 'nee'

    ret['enkel sdgezicht'] = 'ja' if \
        ret['sdgezicht'] > 0 and \
        ret ['monument'] == 0 and \
        ret['landschap'] == 0 else 'nee'

    ret['enkel landschap'] = 'ja' if \
        ret['landschap'] > 0 and \
        ret ['sdgezicht'] == 0 and \
        ret['monument'] == 0 else 'nee'

    return ret

def analyseer_relaties(erfgoedobject):
    '''
    Zoek de relaties van het type omvat en is deel van van een erfgoedobject
    op.
    '''

    erfgoedobjecten = [e for e in erfgoedobject['relaties'] if e['verwant']['id'] == 4]

    ret = {
        'omvat': [e['uri'] for e in erfgoedobjecten if e['relatietype']['id'] == 7],
        'deel van': [e['uri'] for e in erfgoedobjecten if e['relatietype']['id'] == 6]
    }

    return ret

def get_id(uri):
    return uri.split('/')[-1]

def clean_relaties(erfgoedobjecten):
    '''
    Kuis de 'deel van' en 'omvat' relaties op zodat enkel de relaties
    overblijven met andere erfgoedobjecten in dezelfde lijst.
    '''
    search = [e['uri'] for e in erfgoedobjecten]
    for e in erfgoedobjecten:
        e['deel van'] = ", ".join([get_id(dv) for dv in e['deel van'] if dv in search])
        e['omvat'] = ", ".join([get_id(omv) for omv in e['omvat'] if omv in search])
    return erfgoedobjecten

def analyseer_kenmerkgroepen(erfgoedobject, concept):
    '''
    Zoek de typologie, datering en stijl op van een erfgoedobject en de
    primaire kenmerkgroep(en)
    '''
    def get_termen(kenmerk_id):
        termen = []
        for k in erfgoedobject['kenmerkgroepen']:
            for t in k['thesaurus']:
                if t['kenmerk']['id'] == kenmerk_id:
                    termen.append(t['label'])
        return list(set(termen))

    prim_kmgr = []
    if concept:
        prim_kmgr = zoek_primaire_kenmerkgroepen(erfgoedobject, concept)

    return {
        'typologie': ", ".join(get_termen(3)),
        'datering': ", ".join(get_termen(8)),
        'stijl': ", ".join(get_termen(5)),
        'primaire kenmerkgroepen': ", ".join(
            [" | ".join(t['label'] for t in k['thesaurus']) for k in prim_kmgr]
        )
    }

def zoek_primaire_kenmerkgroepen(erfgoedobject, concept):
    '''
    Zoek de kenmerkgroepen waaraan deze typologie of één van zijn kinderen is toegekend
    '''
    exp = get_erfgoedtypes().expand(concept.id)
    expanded_concepts = []
    for c in exp:
        expanded_concepts.append(get_erfgoedtypes().get_by_id(c).uri)

    allek = None
    kmgr = erfgoedobject['kenmerkgroepen']

    # Nagaan of er een "alle kenmerkgroepen" is en de typologie uit die groep
    # toekennen aan alle kenmerkgroepen
    allek = [k for k in kmgr if k['alle_kenmerkgroepen']]
    if len(allek):
        for k in kmgr:
            if not k['id'] == allek[0]['id']:
                k['thesaurus'].extend(allek[0]['thesaurus'])
            else:
                del k

    prim_kmgr = []
    for k in kmgr:
        for t in k['thesaurus']:
            if t['kenmerk']['id'] == 3 and t['uri'] in expanded_concepts:
                prim_kmgr.append(k)
                continue

    return prim_kmgr
