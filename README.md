# Onroerend Erfgoed Abacus

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.6533854.svg)](https://doi.org/10.5281/zenodo.6533854)

Scripts om erfgoed uit de [Inventaris Onroerend
Erfgoed](https://inventaris.onroerenderfgodd.be) correct te helpen tellen.

## Type tellen

Het script *type_tellen* kan gebruikt worden om het aantal erfgoedobjecten van 
een bepaalde erfgoedtype te tellen. Kan gecombineerd worden met types die niet 
mogen meetellen voor dingen zoals "kerken, maar geen abdijkerken" of met zaken 
zoals de rechtsgevolgen en de erfgoedwaarde. Om het script te gebruiken, stel
je een aantal parameters in:

**DISCIPLINE = None**

Ofwel *None* om aan te geven dat alle disciplines gevraagd worden, ofwel een
list van disciplines (1, 2, 3, 4). Meestal is discipline 4 (varend erfgoed) niet
relevant. Voor het tellen van zaken zoals kerken of fonteinen is het vaak
nuttig om enkel de discipline *bouwkundig erfgoed (2)* te gebruiken.

**ERFGOEDWAARDE = None**

Ofwel *None* om aan te geven dat de huidige erfgoedwaarde geen rol speelt, of
een boolean *True* of *False* om aan te geven dat we enkel erfgoedobjecten
zoeken waarvan de erfgoedwaarde nog aanwezig is of erfgoedobjecten waarvan de
erfgoedwaarde niet meer aanwezig is (weinig relevat).

**RECHTSGEVOLGEN = None**

Ofwel *None* om aan te geven dat we alle erfgoedobjecten tellen, ongeacht de
gekoppelde beschermingen, ofwel een string zoals `zonder rechtsgevolgen`, `met
rechtsgevolgen`, `beschermd`, `vastgesteld`.

**CONCEPT = None**

Ofwel *None* om aan te geven dat alle erfgoedobjecten van alle types tellen,
ofwel een id van een erfgoedtype uit de thesaurus
[ERFGOEDTYPES](https://thesaurus.onroerenderfgoed.be/conceptschemes/ERFGOEDTYPES).
Indien dit op *None* blijft staan, kan dit ongeveer de volledige databank aan
gegevens opleveren. Dit is zelden de bedoeling en zou dan moeten gecombineerd
worden met een parameter *RECHTSGEVOLGEN = `beschermd`* en *DISCIPLINE = [4]*
zodat het zoekresultaat niet te groot wordt.

**NOT_CONCEPT = []**

Ofwel een lege list om aan te geven dat er geen erfgoedtypes moeten weggelaten
worden, ofwel een list met id's van erfgoedtypes. Deze parameter werkt enkel
indien er ook een *CONCEPT* ingevuld is en kan gebruikt wordt om bv. te zoeken
naar *katholieke kerken* maar geen *abdijkerken*

### Voorbeelden

* *DISCIPLINE = [4]* en *RECHTSGEVOLGEN = `beschermd`*: al het beschermd varend
    erfgoed
* *DISCIPLINE = [2, 3]* en *RECHTSGEVOLGEN = `beschermd`* en *CONCEPT = 230* en
    *NOT_CONCEPT = [6, 52, 242]*: alle beschermde katholieke kerken die geen abdijkerk,
    begijnhofkerk of kloosterkerk zijn.
* *DISCIPLINE = [2, 3]* en *RECHTSGEVOLGEN = `beschermd`* en *CONCEPT = 514*:
    alle beschermde windmolens
