# Nutrilog – így kelted életre

Kalória-, makró- és mikrotápanyag-napló, amely telefonon úgy viselkedik, mint egy közönséges app. A felülete angol, de magyarul és angolul is kereshetsz benne (tojás, kenyér, kecskesajt, egg, chicken breast).

Az egész kb. 25 percig tart, ingyenes, és nem kell hozzá programozni. A lényeg: feltöltöd a fájlokat egy ingyenes tárhelyre (GitHub Pages), az ad neked egy webcímet, te pedig a telefonodon felteszed a kezdőképernyőre.

**Mi kell hozzá:** egy számítógép (Windows vagy Mac), egy e-mail-cím és a telefonod.

**Három szó, amit a GitHub használ:**
- *repository* („repó”): egy mappa a GitHubon, ide kerülnek a fájljaid
- *commit*: a feltöltés véglegesítése, olyan, mint egy „Mentés” gomb
- *Pages*: a GitHub ingyenes weboldal-szolgáltatása, ettől lesz webcíme az appnak

---

## 1. Csomagold ki a zip-fájlt

1. Keresd meg a letöltött `nutrilog.zip` fájlt.
2. **Windows:** kattints rá jobb gombbal, válaszd az „Extract All…” menüpontot, majd „Extract”. **Mac:** kattints rá duplán.
3. Nyisd meg a kicsomagolt mappát. Benne kell lennie többek között az `index.html`, az `app.js`, a `ciqual.json` és az `usda.json` fájlnak.

## 2. Hozz létre GitHub-fiókot

1. Nyisd meg a **github.com** oldalt, és kattints a „Sign up” gombra.
2. Add meg az e-mail-címedet, válassz jelszót és felhasználónevet.
3. A felhasználónév bekerül az app webcímébe, ezért olyat válassz, amit nem bánsz.
4. A GitHub kódot küld az e-mail-címedre. Írd be, ezzel megerősíted a fiókot.

## 3. Hozz létre egy repository-t

1. Belépés után kattints a jobb felső sarokban a **+** jelre, majd a „New repository” menüpontra.
2. „Repository name”: írd be, hogy `nutrilog`.
3. Válaszd a **Public** lehetőséget. Ingyenes fiókkal a Pages csak nyilvános repóból megy. Ettől nem lesz nyilvános a naplód: az adataid sosem kerülnek a GitHubra, csak az app fájljai.
4. **Ne pipálj ki semmit** a „Add a README file”, „.gitignore” és „license” sorokban.
5. Kattints a zöld „Create repository” gombra.

## 4. Töltsd fel a fájlokat

1. Az új, üres repón még nincs „Add file” gomb, az csak az első feltöltés után jelenik meg. Az oldal közepén, a „Quick setup” részben ott van egy mondat: „Get started by creating a new file or **uploading an existing file**”. Kattints az „**uploading an existing file**” kék linkre. Ha a link nem látszik, írd be a böngésző címsorába a repód címét ezzel a véggel: `https://github.com/FELHASZNÁLÓNEVED/nutrilog/upload/main`
2. Nyisd meg a kicsomagolt mappát, és jelöld ki az összes fájlt benne (**Windows:** Ctrl+A, **Mac:** Cmd+A).
3. Húzd át őket a böngészőablakba, a „Drag files here” feliratra. **Csak a fájlokat húzd, magát a mappát ne.**
4. Várj, amíg minden fájl mellett kész a töltősáv. 14 fájlnak kell megjelennie.
5. Görgess le, és kattints a zöld „**Commit changes**” gombra. Ha választani kell, hogy hova mentsen, a „Commit directly to the main branch” a jó.
6. Ellenőrizd: a repó főoldalán látnod kell az `index.html`-t és a többi fájlt.

## 5. Kapcsold be a Pages-t

1. A repó tetején kattints a **Settings** fülre. Ha nem látod, nyisd le a „…” menüt, ott van.
2. A bal oldali listában kattints a **Pages** menüpontra.
3. A „Build and deployment” részben a „Source” legyen **Deploy from a branch**.
4. A „Branch” alatt válaszd a **main** ágat, mellette a mappánál a **/ (root)** lehetőséget, majd kattints a **Save** gombra.
5. Várj pár percet. A GitHub szerint akár 10 percig is eltarthat. Frissítsd az oldalt időnként.
6. Amikor kész, az oldal tetején megjelenik, hogy „Your site is live at…”, és egy „Visit site” gomb. A cím így néz ki: `https://FELHASZNÁLÓNEVED.github.io/nutrilog/`
7. Kattints a „Visit site” gombra. Ha megjelenik az app, minden rendben.

## 6. Tedd fel a telefonodra

Nyisd meg a fenti címet a telefonodon.

**iPhone** (Safarival kell megnyitnod):
1. Koppints alul a Megosztás gombra (négyzet felfelé mutató nyíllal).
2. Görgess lefelé, és koppints az „**Add to Home Screen**” sorra.
3. Koppints jobb felül az „Add” gombra.

**Android** (Chrome):
1. Koppints jobb felül a három pontra (⋮).
2. Válaszd az „**Install app**” vagy az „**Add to Home screen**” menüpontot.
3. Hagyd jóvá.

Ezután a kezdőképernyőn ott lesz a Nutrilog ikonja (fekete négyzet, benne háromszínű fánkdiagram). Innen indítsd, ne a böngészőből. Az első megnyitáshoz internet kell, mert ekkor tölti le az 1,4 MB-os élelmiszer-adatbázist. Utána internet nélkül is megy, kivéve a vonalkódos keresést és az Open Food Facts keresést.

## 7. Első használat

**Étel felvétele:**
1. A Diary fülön koppints a „**Log food**” gombra.
2. Írd be, hogy `főtt tojás` (vagy `boiled egg`), és koppints az „Egg, hard-boiled” sorra.
3. Az „Amount” ablakban a mennyiség grammban látszik, alapból 100. Koppints a számra, és írd át (pl. `50`). A tizedest ponttal és vesszővel is írhatod (`1,5` és `1.5` ugyanaz). A kék gomb felirata megmondja, mit rögzítesz, például „Add 50 g”.
   Az étkezés alapból az, amelyikbe aznap utoljára vittél fel valamit (üres napon Meal 1). A „Meal” listából átállíthatod, Meal 1-től Meal 6-ig.
   Mellette a „Time” mező az étel felvételének időpontját mutatja, alapból a pillanatnyi időt. Ha korábban ettél, koppints a mezőre, és állítsd be a valódi időpontot (az iPhone görgethető időválasztót ad). A nap dátuma nem változik: az mindig az a nap, amelyik a Diary tetején látszik.
   Ha készen vagy, koppints a kék gombra.
4. A találatok három helyről jönnek, ebben a sorrendben: „CIQUAL (generic foods)” (francia átlagok), „USDA (generic foods, US)” (amerikai átlagok), végül az „Open Food Facts” (csomagolt termékek, ezt külön gombbal kéred). Az USDA-ból először 10 találat látszik, a „**Show more USDA results**” gombbal újabbakat kapsz. Az USDA-soron a „SR Legacy” vagy „Foundation” felirat és egy „FDC” szám látszik: ez az USDA saját azonosítója, a fdc.nal.usda.gov oldalon rá tudsz keresni. Az USDA ételeknél az Amount ablakban gyorsgombok vannak a háztartási mértékekkel (például „1 large”, „1 cup, chopped”), a mennyiség viszont alapból 100 g marad.
5. A tétel megjelenik a naplóban, a neve alatt az időponttal (pl. `07:45 · 100 g · CIQUAL`). Egy étkezésen belül a tételek idő szerint követik egymást. Ha módosítani (a mennyiséget, az étkezést vagy az időpontot) vagy törölni akarod, koppints rá.

**Csomagolt termék vonalkóddal:**
1. Koppints a „**Scan**” gombra, és engedélyezd a kamerát.
2. Tartsd a vonalkódot a kamera elé. Az app az Open Food Facts adatbázisból tölti le a tápértéket.
3. Ha a kamera nem megy, a „or type the number” mezőbe begépelheted a vonalkód számjegyeit, és koppinthatsz a „Look up” gombra.
4. A vonalkódos keresés az egész világ termékei között keres, nem csak a magyarok között. Az Open Food Facts viszont közösségi adatbázis, ezért hiányozhatnak belőle termékek, főleg étrend-kiegészítők és Európán kívüli áruk. Ilyenkor az app ezt írja: „Open Food Facts does not have barcode…”. Koppints a kék „Create food from label” gombra, és másold be az értékeket a csomagolásról. A vonalkód már be van írva, és a következő beolvasásnál az app azonnal a saját ételedet hozza.
5. Ha nevet írsz be, a találatok alatt van az „Open Food Facts” rész, benne a „Search … in Open Food Facts” gombbal. Ez alapból az egész világon keres. Ha csak a Magyarországon árult termékeket akarod látni, pipáld be alatta az „Only products sold in Hungary” négyzetet.

**Étel vagy kiegészítő felvétele a címkéről:**
1. Koppints a „**Create food**” gombra (a Diary fülön vagy a My foods fülön).
2. Írd be a nevét. Kapszulánál vagy tablettánál válaszd az „1 unit” lehetőséget, és írd mellé, hogy `capsule`.
3. Az „Essentials” részben van a kalória, a fehérje, a szénhidrát, a cukor, a zsír, a telített zsír, a rost és a só. Ha a címkén vitaminok, ásványi anyagok vagy zsírsavak is szerepelnek, nyisd le a „More values” részt. **Amit nem tudsz, hagyd üresen**: az üres mező „nincs adat”, a 0 pedig valódi nulla.
4. „Save”. Ha nem adsz nevet, az app a Name mező alatt szól, és oda viszi a kurzort. Mentés után a „Log food” keresőjében név szerint megtalálod, a My foods fülön pedig a saját ételeid listáját látod.

**Hogyan olvasd a Nutrients fület:**
- A `≥` jel azt jelenti: legalább ennyi. Hiányzó adatnál az összeg alsó becslés, mert az app a hiányt nem tekinti nullának.
- A jobb oldali jelvény (pl. `4/6`) azt mutatja, hogy a nap hat tételéből négyhez van adat az adott tápanyagról. A tápanyagra koppintva látod, melyik tételből hiányzik.
- A `~` jel az energia előtt azt jelzi, hogy a CIQUAL nem közölt kalóriát, és a fehérjéből, szénhidrátból és zsírból számoltuk ki.

**NOVA: mennyire feldolgozott, amit eszel:**
A Nutrients fül tetején van a „**Food processing (NOVA)**” kártya. A NOVA az ételeket négy csoportba sorolja aszerint, hogy mennyire ipari: az 1-es a feldolgozatlan vagy minimálisan feldolgozott étel (zöldség, gyümölcs, tojás, tej, nyers hús, rizs), a 2-es a konyhai alapanyag (olaj, vaj, cukor, só), a 3-as a feldolgozott étel (konzerv, sajt, friss kenyér), a 4-es az ultrafeldolgozott étel (üdítő, chips, édesség, instant leves, felvágott). A kártya azt mutatja, hogy a nap energiájának hány százaléka esik az egyes csoportokra. Az „Unclassified” sor azt a részt mutatja, amelyhez még nincs csoport. A százalékok mindig 100-ra jönnek ki, és csak azokat a tételeket számolják, amelyeknek van energia-adata.
Az app **nem találgat**: a CIQUAL és az USDA ételeknél nincs NOVA-adat, az Open Food Facts termékeknél csak egy részénél van. Ezért a legtöbb étel eleinte „Unclassified”, és te állítod be egyszer, kézzel:
1. A Nutrients fülön koppints a kártya alatti „**Set NOVA groups**” sorra. Mellette látod, hány étel vár besorolásra.
2. Az „Unclassified” listában a legtöbb energiát adó étel van legfelül. Minden sor végén négy kör van: 1, 2, 3, 4. Koppints arra a számra, amelyik az ételre szerinted illik. Az étel átkerül a „Classified” listába, és a kártya azonnal frissül.
3. Ha elnyomtad, alul megjelenik egy értesítés az „**Undo**” gombbal. Utólag is javíthatsz: a „Classified” listában koppints másik számra, vagy a már kijelölt számra újra, akkor a besorolás törlődik.
4. A választás magához az ételhez tartozik, ezért minden más napon is él. Egy ételt elég egyszer besorolni. A „Create food” ételeknél ugyanez a mező az étel szerkesztésénél is megvan („Food-processing group”), és a kettő mindig ugyanazt mutatja.
5. A „What are the NOVA groups?” sor rövid leírást ad a négy csoportról példákkal.
A NOVA a feldolgozottság mértéke, nem az egészséges voltáé. A besorolás ítélet kérdése, a hozzávalók és a márka sokat számítanak, ezért a saját ételeidnél érdemes átgondolni. A Diary fülön is látszik egy szürke sor az ultrafeldolgozott (4-es) ételek energiaarányával, amint legalább egy ételnek van csoportja.

**Világos vagy sötét téma:**
1. Koppints a **Data** fülre. Legfelül van az „**Appearance**” kártya három gombbal.
2. „Auto”: az app a telefonod beállítását követi, és magától vált, ha a telefon vált (például este). „Light”: mindig világos. „Dark”: mindig sötét.
3. A választás megmarad, amikor bezárod és újra megnyitod az appot. Az adatmentésnek (JSON) nem része, ezért új telefonon újra be kell állítanod.

## 8. Mentsd rendszeresen az adataidat

Az adataid csak a telefonodon vannak, a böngésző tárhelyén, a GitHubon nincsenek. Ha törlöd a böngészőadatokat vagy telefont cserélsz, elvesznek. Az iPhone Safari ráadásul törölheti egy weboldal adatait, ha hét napig nem használod. A kezdőképernyőre tett appra ez nem vonatkozik, ezért iPhone-on mindig onnan indítsd.

1. Nyisd meg a **Data** fület. A „Storage” kártya megmondja, védi-e a böngésző az adataidat („Persistent”), vagy törölheti őket („Not persistent”). Koppints a „**Save backup (JSON)**” gombra.
2. A fájl a letöltések közé kerül. Másold át a felhőbe (Google Drive, iCloud) vagy küldd el magadnak e-mailben.
3. Heti egy mentés elég. A mentésben benne vannak a naplóbejegyzések, a saját ételeid és a NOVA-besorolásaid is. Visszatöltés: Data fül, „Restore from file”.
4. **Ne töltsd fel a mentésfájlt a GitHubra.** Az nyilvános lenne.

## 9. Elemzés Claude-dal

A Data fülön a „**Daily totals (CSV)**” minden naphoz tartalmazza az összes tápanyagot. Az üres cella azt jelenti, hogy nincs adat. A `__max` végű oszlopok a „< x” értékek felső határát adják, a `__n` oszlopok pedig azt, hogy hány tételből van adat. Az „Entries (CSV)” ugyanezt tételenként mutatja: a `source` oszlop megmondja, honnan jön az étel (`ciqual`, `usda`, `off` vagy `user`), a `date` oszlop a nap, a `time` oszlop a tétel időpontja (óra:perc, 24 órás), a `nova` oszlop az étel NOVA-csoportja (1–4, üres, ha nincs besorolva), az étkezés oszlopában „Meal 1”, „Meal 2” stb. áll. A régebbi tételeknél, amelyekhez még nem mentettünk időpontot, az app a felvétel pillanatát írja. Töltsd fel valamelyiket egy beszélgetésbe vagy projektbe.

## 10. Hogyan frissítesz egy új verzióra

1. Csomagold ki az új zip-et.
2. Nyisd meg a repót a GitHubon, kattints az „Add file” gombra, majd az „Upload files” menüpontra.
3. Húzd be az új fájlokat. Az azonos nevűeket a GitHub felülírja.
4. „Commit changes”. Pár perc múlva az új verzió él.
5. A telefonon nyisd meg az appot, és nézd meg a Data fül alján az „App version” kártyát. Ha ott még a régi verziószám áll, koppints a „Reload app files” gombra (internet kell hozzá). Az adataid megmaradnak, csak az app fájljai töltődnek le újra.

## Ha elakadsz

| Mit látsz | Mit csinálj |
|---|---|
| A webcím „404”-et ad | Várj 10 percet, és ellenőrizd, hogy az `index.html` a repó főoldalán van-e, nem almappában. Ha almappában van, töltsd fel újra a fájlokat. |
| „The app could not start” | Az `index.html`-re duplán kattintva az app nem indul, mert tárhely kell hozzá. Nyisd meg a GitHub-címről. |
| Üres oldal vagy régi verzió | Data fül → „App version” kártya → „Reload app files”. Ha az app el sem indul, frissítsd az oldalt, vagy zárd be és nyisd meg újra. |
| A kamera nem indul | Engedélyezd a kamerát a telefon beállításaiban a böngészőnek. Addig is beírhatod a vonalkód számjegyeit a „Scan” ablakban. |
| Az „Amount” mezőre koppintva nem jön fel a billentyűzet | Koppints közvetlenül a számra. Ha így sem jön fel a billentyűzet, használd a gyorsgombokat (10 g, 30 g, 50 g…), és szólj nekem. |
| A „Time” mező 12 órás formában (AM/PM) mutatja az időt | A mező a telefon beállítását követi. Az iPhone-on: Settings → General → Date & Time → kapcsold be a „24-Hour Time” kapcsolót. A naplóban és a CSV-ben az idő mindig 24 órás. |
| „The USDA food data could not be loaded” a naplóban, vagy nincsenek USDA-találatok | Az `usda.json` fájl nem töltődött le. Kapcsold be az internetet, majd Data fül → „Reload app files”. Az USDA-tételek addig rejtve vannak, törölve nincsenek. |
| A Nutrients fülön az „Unclassified” sor 100% | A NOVA-csoportot neked kell beállítanod: Nutrients fül → „Set NOVA groups” → koppints az 1–4 számokra az ételek mellett. A CIQUAL és USDA ételekhez nincs beépített besorolás. |
| „Open Food Facts does not have barcode…” | A termék nincs az adatbázisban. Használd a „Create food from label” gombot. |
| „Open Food Facts is not available right now” | Az adatbázis szervere éppen nem válaszol. Próbáld újra egy perc múlva. |
| „Could not reach Open Food Facts” | Ellenőrizd az internetet. Hiányos vagy hiányzó terméknél használd a „Create food” gombot. |
| Eltűnt az adatom | Töltsd vissza a legutóbbi mentést: Data fül, „Restore from file”. Az app megerősítést kér, mielőtt felülírja az adataidat. |

## Amit érdemes tudnod

- Az általános élelmiszerek adatai a francia CIQUAL 2020 táblából jönnek (3186 étel, 64 tápanyag, francia piaci átlagok, angol nevekkel). A magyar termékeknél a legközelebbi megfelelőt kapod, a pontos érték a címkén van.
- Az USDA adatai az amerikai mezőgazdasági minisztérium FoodData Central adatbázisából jönnek: a Foundation Foods (2026. április, 436 étel) és az SR Legacy (2018, 7793 étel) táblából. Ezek amerikai piaci átlagok, szabadon felhasználható közkincsek. Amit az USDA nem mér, azt az app „nincs adat”-nak hagyja, nem nullának. Három dolgot számolunk: a sót a nátriumból (nátrium × 2,5), a nyers fehérjét a nitrogénből (× 6,25, csak a Foundation ételeknél), és a D-vitamint a nemzetközi egységből (IU × 0,025), ha csak az van megadva. A K2-vitamin az USDA-nál csak az MK-4 forma. A zsírsavaknál csak a pontosan azonosított értéket vettük át, ezért ott több a hiányzó adat. A Foundation táblában néhány étel azonos néven többször szerepel (több minta), ilyenkor az FDC szám különbözteti meg őket.
- A csomagolt termékek az Open Food Facts közösségi adatbázisból jönnek. A címkeadat hiányos vagy hibás lehet, ezért érdemes összevetni a csomagolással.
- Italoknál az app grammal számol, és 1 ml-t 1 g-nak vesz. Hígabb italoknál ez elég pontos.
- Ez egy tájékoztató eszköz, nem orvosi tanács.

**Források:** Anses. 2020. Ciqual French food composition table, <https://doi.org/10.5281/zenodo.4770202> (CC BY 4.0). U.S. Department of Agriculture, Agricultural Research Service. FoodData Central, <https://fdc.nal.usda.gov> (U.S. public domain). Open Food Facts, <https://world.openfoodfacts.org> (ODbL). Vonalkód-olvasó: ZXing-js (Apache 2.0, lásd `ZXING-LICENSE.txt`).
