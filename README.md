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
3. Nyisd meg a kicsomagolt mappát. 14 fájlnak kell benne lennie, köztük az `index.html`, az `app.js` és a `ciqual.json`.

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
1. A Diary fülön koppints az „**Add food**” gombra.
2. Írd be, hogy `főtt tojás` (vagy `boiled egg`), és koppints az „Egg, hard-boiled” sorra.
3. Az „Amount” ablakban írd be a mennyiséget grammban (pl. `50`), válaszd ki az étkezést a „Meal” listából (Meal 1-től Meal 6-ig), és koppints az „Add” gombra. A tizedest ponttal és vesszővel is írhatod (`1,5` és `1.5` ugyanaz).
4. A tétel megjelenik a naplóban. Ha módosítani vagy törölni akarod, koppints rá.

**Csomagolt termék vonalkóddal:**
1. Koppints a „**Scan**” gombra, és engedélyezd a kamerát.
2. Tartsd a vonalkódot a kamera elé. Az app az Open Food Facts adatbázisból tölti le a tápértéket.
3. Ha a kamera nem megy, a „or type the number” mezőbe begépelheted a vonalkód számjegyeit, és koppinthatsz a „Look up” gombra.
4. A vonalkódos keresés az egész világ termékei között keres, nem csak a magyarok között. Az Open Food Facts viszont közösségi adatbázis, ezért hiányozhatnak belőle termékek, főleg étrend-kiegészítők és Európán kívüli áruk. Ilyenkor az app ezt írja: „Open Food Facts does not have barcode…”. Koppints a kék „New food from label” gombra, és másold be az értékeket a csomagolásról. A vonalkód már be van írva, és a következő beolvasásnál az app azonnal a saját ételedet hozza.
5. A névkeresésnél („Search Open Food Facts”) alapból az egész világon keres. Ha csak a Magyarországon árult termékeket akarod látni, pipáld be a „Name search: only products sold in Hungary” négyzetet.

**Étel vagy kiegészítő felvétele a címkéről:**
1. Koppints a „**New food**” gombra.
2. Írd be a nevét. Kapszulánál vagy tablettánál válaszd az „1 unit” lehetőséget, és írd mellé, hogy `capsule`.
3. Töltsd ki azokat a mezőket, amelyek a címkén szerepelnek. **Amit nem tudsz, hagyd üresen**: az üres mező „nincs adat”, a 0 pedig valódi nulla.
4. „Save”, majd az „Add food”-nál név szerint megtalálod.

**Hogyan olvasd a Nutrients fület:**
- A `≥` jel azt jelenti: legalább ennyi. Hiányzó adatnál az összeg alsó becslés, mert az app a hiányt nem tekinti nullának.
- A jobb oldali jelvény (pl. `4/6`) azt mutatja, hogy a nap hat tételéből négyhez van adat az adott tápanyagról. A tápanyagra koppintva látod, melyik tételből hiányzik.
- A `~` jel az energia előtt azt jelzi, hogy a CIQUAL nem közölt kalóriát, és a fehérjéből, szénhidrátból és zsírból számoltuk ki.

## 8. Mentsd rendszeresen az adataidat

Az adataid csak a telefonodon vannak, a böngésző tárhelyén, a GitHubon nincsenek. Ha törlöd a böngészőadatokat vagy telefont cserélsz, elvesznek. Az iPhone Safari ráadásul törölheti egy weboldal adatait, ha hét napig nem használod. A kezdőképernyőre tett appra ez nem vonatkozik, ezért iPhone-on mindig onnan indítsd.

1. Nyisd meg a **Data** fület, és koppints a „**Save backup (JSON)**” gombra.
2. A fájl a letöltések közé kerül. Másold át a felhőbe (Google Drive, iCloud) vagy küldd el magadnak e-mailben.
3. Heti egy mentés elég. Visszatöltés: Data fül, „Restore from file”.
4. **Ne töltsd fel a mentésfájlt a GitHubra.** Az nyilvános lenne.

## 9. Elemzés Claude-dal

A Data fülön a „**Daily totals (CSV)**” minden naphoz tartalmazza az összes tápanyagot. Az üres cella azt jelenti, hogy nincs adat. A `__max` végű oszlopok a „< x” értékek felső határát adják, a `__n` oszlopok pedig azt, hogy hány tételből van adat. Az „Entries (CSV)” ugyanezt tételenként mutatja, az étkezés oszlopában „Meal 1”, „Meal 2” stb. áll. Töltsd fel valamelyiket egy beszélgetésbe vagy projektbe.

## 10. Hogyan frissítesz egy új verzióra

1. Csomagold ki az új zip-et.
2. Nyisd meg a repót a GitHubon, kattints az „Add file” gombra, majd az „Upload files” menüpontra.
3. Húzd be az új fájlokat. Az azonos nevűeket a GitHub felülírja.
4. „Commit changes”. Pár perc múlva az új verzió él.
5. A telefonon zárd be az appot, és nyisd meg újra, szükség esetén kétszer. Az adataid megmaradnak.

## Ha elakadsz

| Mit látsz | Mit csinálj |
|---|---|
| A webcím „404”-et ad | Várj 10 percet, és ellenőrizd, hogy az `index.html` a repó főoldalán van-e, nem almappában. Ha almappában van, töltsd fel újra a fájlokat. |
| „The app could not start” | Az `index.html`-re duplán kattintva az app nem indul, mert tárhely kell hozzá. Nyisd meg a GitHub-címről. |
| Üres oldal vagy régi verzió | Frissítsd az oldalt, vagy zárd be és nyisd meg újra az appot. |
| A kamera nem indul | Engedélyezd a kamerát a telefon beállításaiban a böngészőnek. Addig is beírhatod a vonalkód számjegyeit a „Scan” ablakban. |
| Az „Amount” mezőre koppintva nem jön fel a billentyűzet | Koppints közvetlenül a számra. Az első koppintásnál a régi érték szürke háttérszámmá válik, és az új szám a helyére kerül. Ha így sem jön fel a billentyűzet, használd a gyorsgombokat (10 g, 30 g, 50 g…), és szólj nekem. |
| „Open Food Facts does not have barcode…” | A termék nincs az adatbázisban. Használd a „New food from label” gombot. |
| „Open Food Facts is not available right now” | Az adatbázis szervere éppen nem válaszol. Próbáld újra egy perc múlva. |
| „Could not reach Open Food Facts” | Ellenőrizd az internetet. Hiányos vagy hiányzó terméknél használd a „New food” gombot. |
| Eltűnt az adatom | Töltsd vissza a legutóbbi mentést: Data fül, „Restore from file”. |

## Amit érdemes tudnod

- Az általános élelmiszerek adatai a francia CIQUAL 2020 táblából jönnek (3186 étel, 64 tápanyag, francia piaci átlagok, angol nevekkel). A magyar termékeknél a legközelebbi megfelelőt kapod, a pontos érték a címkén van.
- A csomagolt termékek az Open Food Facts közösségi adatbázisból jönnek. A címkeadat hiányos vagy hibás lehet, ezért érdemes összevetni a csomagolással.
- Italoknál az app grammal számol, és 1 ml-t 1 g-nak vesz. Hígabb italoknál ez elég pontos.
- Ez egy tájékoztató eszköz, nem orvosi tanács.

**Források:** Anses. 2020. Ciqual French food composition table, <https://doi.org/10.5281/zenodo.4770202> (CC BY 4.0). Open Food Facts, <https://world.openfoodfacts.org> (ODbL). Vonalkód-olvasó: ZXing-js (Apache 2.0, lásd `ZXING-LICENSE.txt`).
