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
3. Nyisd meg a kicsomagolt mappát. Benne kell lennie többek között az `index.html`, az `app.js`, a `ciqual.json`, az `usda.json` és a `dmbio.json` fájlnak.

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
   Mellette a „Time (24 h)” mező az étel felvételének időpontját mutatja, alapból a pillanatnyi időt. Ha korábban ettél, koppints a mezőre, és írd be a valódi időpontot számokkal: a `1745` beírásakor az app magától `17:45`-öt csinál belőle (a kettőspontot nem kell beírnod). Mindig 24 órás, a telefon 12/24 órás beállításától függetlenül. A nap dátuma nem változik: az mindig az a nap, amelyik a Diary tetején látszik.
   Ha készen vagy, koppints a kék gombra.
4. A találatok négy helyről jönnek, ebben a sorrendben: „dmBio (dm.hu products)” (a dm drogéria bio termékei, lásd alább), „CIQUAL (generic foods)” (francia átlagok), „USDA (generic foods, US)” (amerikai átlagok), végül az „Open Food Facts” (csomagolt termékek, ezt külön gombbal kéred). A saját ételeid, ha vannak, mindig legfelül állnak. Az USDA-ból először 10 találat látszik, a „**Show more USDA results**” gombbal újabbakat kapsz. Az USDA-soron a „SR Legacy” vagy „Foundation” felirat és egy „FDC” szám látszik: ez az USDA saját azonosítója, a fdc.nal.usda.gov oldalon rá tudsz keresni. Az USDA ételeknél az Amount ablakban gyorsgombok vannak a háztartási mértékekkel (például „1 large”, „1 cup, chopped”), a mennyiség viszont alapból 100 g marad.
5. A tétel megjelenik a naplóban, a neve alatt az időponttal (pl. `07:45 · 100 g · CIQUAL`). Egy étkezésen belül a tételek idő szerint követik egymást. Ha módosítani (a mennyiséget, az étkezést vagy az időpontot) vagy törölni akarod, koppints rá.

**dmBio termékek (dm drogéria):**
1. A „Log food” keresőben a találatok tetején a „**dmBio (dm.hu products)**” rész áll. Írj be egy nevet magyarul (`olívaolaj`) vagy angolul (`olive oil`), vagy a vonalkód számjegyeit. Elsőre 10 sor látszik, a „**Show more dmBio results**” gombbal újabb 30.
2. A „Scan” gomb a dmBio termékeket **internet nélkül** is megtalálja. Az app a vonalkódot előbb a saját ételeid között keresi, utána a dmBio termékek között, és csak a végén kérdezi az Open Food Facts-et.
3. Az „Amount” ablakban koppints az „**Estimated values · confidence …**” sorra. Megmutatja, mely értékek jönnek a dm.hu címkéjéről (energia, fehérje, szénhidrát, zsír, cukor, rost, telített zsír, só, néha több), és melyek **becslések** a hozzávalók listájából (CIQUAL-adatokkal). A „confidence” a becslés megbízhatósága: high, medium, low, very low vagy none. A „none” terméknél (például kávé, tea) semmi nincs becsülve, és a dm.hu-n sincs tápértéktáblázat hozzá.
4. Folyékony vagy porból készülő terméknél külön gyorsgombok vannak. Az olajoknál és szirupoknál a „100 ml”, az „1 tbsp (15 ml)” és az „1 tsp (5 ml)” azt a **grammot** írja be, amennyit az adag nyom (az értékek 100 g-ra vonatkoznak). A leves- és tápszerpornál a „100 ml prepared” és a „0.5 l prepared” azt írja be, hány gramm por van a kész levesben vagy italban.
5. Ha egy termék „fortified” (dúsított) lehet, az ablak figyelmeztet: a vitamin- és ásványianyag-becslés ilyenkor alacsonyabb lehet a valóságosnál.
6. **Figyelem:** a dmBio-becslési projektből kapott `products_dmbio_nutrilog_v3.json` olyan, mint egy mentésfájl. **Ne töltsd vissza a „Restore from file” gombbal**, mert az felülírná a naplódat és a saját ételeidet. Erre nincs szükség: a 527 termék már benne van az appban. Az „Import foods (JSON)” gombra sincs szükség hozzá: az a `dm:` azonosítójú termékeket úgyis kihagyná, mert csak a saját ételeidet tölti be.

**Csomagolt termék vonalkóddal:**
1. Koppints a „**Scan**” gombra, és engedélyezd a kamerát.
2. Tartsd a vonalkódot a kamera elé, **10–20 cm-re, laposan és nyugodtan**, jó fényben. A csillogó fólián a fény visszaverődése sokat ront, ilyenkor dönts egy kicsit a csomagon. Az app akkor fogadja el a számot, ha **többször egymás után ugyanazt olvasta** (ez fél másodperc, ha a kód éles). Ezért kicsit várnia kell, de nem fogad el téves számot. Ha 10 másodperc alatt sem megy, az app ezt írja: „Still looking.” Ilyenkor közelíts vagy távolodj egy kicsit, vagy írd be a számot. Az app a dmBio termékeket a saját adatbázisából hozza, minden más termék tápértékét az Open Food Facts adatbázisból tölti le.
3. Ha a kamera nem megy, a „or type the number” mezőbe begépelheted a vonalkód számjegyeit, és koppinthatsz a „Look up” gombra.
4. A vonalkódos keresés az egész világ termékei között keres, nem csak a magyarok között. Az Open Food Facts viszont közösségi adatbázis, ezért hiányozhatnak belőle termékek, főleg étrend-kiegészítők és Európán kívüli áruk. Ilyenkor az app ezt írja: „Open Food Facts does not have barcode…”. Koppints a kék „Create food from label” gombra, és másold be az értékeket a csomagolásról. A vonalkód már be van írva, és a következő beolvasásnál az app azonnal a saját ételedet hozza.
5. Ha nevet írsz be, a találatok alatt van az „Open Food Facts” rész, benne a „Search … in Open Food Facts” gombbal. Ez alapból az egész világon keres. Ha csak a Magyarországon árult termékeket akarod látni, pipáld be alatta az „Only products sold in Hungary” négyzetet.

**Étel vagy kiegészítő felvétele a címkéről:**
1. Koppints a „**Create food**” gombra (a Diary fülön vagy a My foods fülön).
2. Írd be a nevét. Kapszulánál vagy tablettánál válaszd az „1 unit” lehetőséget, és írd mellé, hogy `capsule`. Ha a címkén az értékek **100 ml-re** vannak megadva (ital, olaj), válaszd a „**100 ml (counted as 100 g)**” lehetőséget: az „Amount” ablakban, a naplóban és a listában ilyenkor ml látszik, a számolás pedig ugyanaz marad, mint grammnál. A lap alján a „Portions” rész ilyenkor ml-ben kéri az adagokat.
3. Az „Essentials” részben van a kalória, a fehérje, a szénhidrát, a cukor, a zsír, a telített zsír, a rost és a só. Ha a címkén vitaminok, ásványi anyagok vagy zsírsavak is szerepelnek, nyisd le a „More values” részt. **Amit nem tudsz, hagyd üresen**: az üres mező „nincs adat”, a 0 pedig valódi nulla.
4. „Save”. Ha nem adsz nevet, az app a Name mező alatt szól, és oda viszi a kurzort. Mentés után a „Log food” keresőjében név szerint megtalálod, a My foods fülön pedig a saját ételeid listáját látod.
5. Ha a címkén csak néhány érték áll, a többit egy AI becsülheti a hozzávalókból, és az app egy lépésben be tudja tölteni az AI válaszát. Ezt a „**Paste from AI**” gomb csinálja, lásd a 12. fejezetet. Kézzel is jelölhetsz becslést: a „Create food” ablakban nyisd le az „**Estimates (optional)**” részt, és koppints a `~` gombra az érték mellett.

**Hogyan olvasd a Nutrients fület:**
- A `≥` jel azt jelenti: legalább ennyi. Hiányzó adatnál az összeg alsó becslés, mert az app a hiányt nem tekinti nullának.
- A jobb oldali jelvény (pl. `4/6`) azt mutatja, hogy a nap hat tételéből négyhez van adat az adott tápanyagról. A tápanyagra koppintva látod, melyik tételből hiányzik.
- A `~` jel az érték előtt azt jelzi, hogy az érték (egy része) **becslés**, nem címkeadat. Az energia előtt azt jelenti, hogy a kalóriát a fehérjéből, szénhidrátból és zsírból számolta ki az app. A dmBio termékeknél azt, hogy a tápanyagot a hozzávalók listájából becsülték. A saját ételeidnél azt, hogy te (vagy az AI-válasz) becslésnek jelölted az értéket. Koppints a tápanyag sorára: az „Estimate, not a label value” sor megmondja, melyik tételek becsültek, és mennyire megbízható a becslés.
- A **Water** (víz) az „Energy & macronutrients” csoportban van, az energia és a makrók mellett. A napi összegben az ételekből és italokból származó víz látszik. A víz nem számít bele a „tracked nutrients” számlálóba (az továbbra is 42 tápanyagot számol).

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

Az adataid alapból csak a telefonodon vannak, a böngésző tárhelyén, a GitHubon nincsenek. Ha törlöd a böngészőadatokat vagy telefont cserélsz, elvesznek. (A 9. fejezetben leírt szinkronnal az adataid egy privát GitHub-repóban is megvannak, de a fájlmentést akkor is érdemes megtartani.) Az iPhone Safari ráadásul törölheti egy weboldal adatait, ha hét napig nem használod. A kezdőképernyőre tett appra ez nem vonatkozik, ezért iPhone-on mindig onnan indítsd.

1. Nyisd meg a **Data** fület. A „Storage” kártya megmondja, védi-e a böngésző az adataidat („Persistent”), vagy törölheti őket („Not persistent”). Koppints a „**Save backup (JSON)**” gombra.
2. A fájl a letöltések közé kerül. Másold át a felhőbe (Google Drive, iCloud) vagy küldd el magadnak e-mailben.
3. Heti egy mentés elég. A mentésben benne vannak a naplóbejegyzések, a saját ételeid és a NOVA-besorolásaid is. Visszatöltés: Data fül, „Restore from file”.
4. **Ne töltsd fel a mentésfájlt a GitHubra.** Az nyilvános lenne.
5. Ha csak **ételeket** akarsz betölteni egy fájlból (például az AI-tól kapott `foods` fájlt), ne a „Restore from file” gombot használd, mert az mindent lecserél. Erre való az „Import foods (JSON)” gomb, lásd a 13. fejezetet.

## 9. Szinkron a telefon és a számítógép között (nem kötelező)

A szinkron a naplódat egy **privát** GitHub-repóba menti, és minden eszközön ugyanazt mutatja: a telefonodon és a számítógép böngészőjében is. Ez nem helyettesíti a fájlmentést (8. fejezet), de megóv attól, hogy az adataid egyetlen készüléken éljenek. A repó csak a tiéd, az app oda írja az adataidat, és a GitHub megőrzi a változások történetét.

**A) Egyszeri előkészítés: privát repó** (számítógépen egyszerűbb)
1. Nyisd meg a <https://github.com/new> oldalt. Be kell lépned.
2. A „**Repository name**” mezőbe írd: `nutrilog-data`.
3. Válaszd a „**Private**” opciót. Ez nagyon fontos: a naplód nem lehet nyilvános. Az app meg is tagadja a csatlakozást egy nyilvános repóhoz.
4. Pipáld be az „**Add a README file**” jelölőnégyzetet (így a repó nem üres).
5. Kattints a „**Create repository**” gombra.

**B) Egyszeri előkészítés: hozzáférési token.** A token egy hosszú jelszó, amellyel az app csak ebbe az egy repóba tud írni. Minden eszközödnek csinálj külön tokent, így ha elveszik a telefon, csak azt az egyet kell visszavonnod.
1. Jobb felül kattints a **profilképedre**, majd a „**Settings**” menüpontra.
2. A bal oldali menüben kattints a „**Developer settings**” pontra.
3. A bal oldalon, a „Personal access tokens” alatt kattints a „**Fine-grained tokens**” pontra.
4. Kattints a „**Generate new token**” gombra.
5. „**Token name**”: például `nutrilog-telefon`.
6. „**Expiration**”: válaszd a leghosszabbat, amit a GitHub felkínál. Ha a token lejár, a szinkron megáll, és az app szól: ilyenkor csinálj újat.
7. „**Repository access**”: válaszd az „**Only select repositories**” opciót, majd a „Selected repositories” listából a `nutrilog-data` repót.
8. „**Permissions**” → „Repository permissions” → „**Contents**” → állítsd „**Read and write**” értékre. Mást ne kapcsolj be.
9. Kattints a „**Generate token**” gombra. A token (`github_pat_` kezdetű hosszú szöveg) **csak most látszik**: másold ki a vágólapra (telefonon hosszan nyomva: „Copy”).

**C) Összekapcsolás az appban**
1. Nyisd meg a **Data** fület, a „**Sync**” kártyán koppints a „**Set up sync**” gombra.
2. „**Repository**”: írd be a GitHub-neved és a repó nevét, például `norbert-vincze/nutrilog-data`.
3. „**Access token**”: illeszd be a vágólapról a tokent.
4. Koppints a „**Connect**” gombra. Az app ellenőrzi, hogy a repó privát-e, aztán elküldi az adataidat. A kártyán a „Last sync” sor mutatja az eredményt.
5. **Második eszköz** (például a számítógép): nyisd meg a böngészőben az app címét, csinálj ott egy új tokent (B lépések, a neve legyen mondjuk `nutrilog-szamitogep`), és ismételd meg a C 1–4 lépést. Az első szinkron letölti a naplódat.

**Így működik**
- A változtatásaid néhány másodperc múlva elmennek. Az app megnyitásakor, amikor visszatérsz hozzá, amikor visszajön az internet, és használat közben 5 percenként is szinkronizál. A „**Sync now**” gombbal kézzel is elindíthatod.
- Ha két eszközön más-más bejegyzést adsz hozzá, mindkettő megmarad. Ha **ugyanazt** a bejegyzést módosítod két eszközön, a későbbi módosítás nyer. Ezért legyen az eszközeid órája automatikus időre állítva.
- A törlés minden eszközön megtörténik. Az „Undo” gomb a szinkronban is visszahozza a bejegyzést.
- Internet nélkül minden működik, a változások akkor mennek el, amikor újra van net. A kártya jelzi, ha vár még valami elküldésre.
- A „Restore from file” szinkron mellett **minden eszközön** lecseréli az adataidat a mentésre (az app erre külön figyelmeztet).
- A repóban fájlok vannak: `entries/ÉÉÉÉ-HH.json` (havonta egy, a naplóbejegyzéseiddel), `foods/` (saját ételek) és `meta.json` (saját adagok, NOVA-besorolások). Ezeket ne szerkeszd kézzel. A GitHubon a „History” gombbal visszanézheted a korábbi állapotokat.
- A token csak azon az eszközön van, ahol beírtad. Nem része a mentésfájlnak, és nem kerül a repóba. **Ne küldd el senkinek, nekem se, és képernyőképen se mutasd meg.** Ha elveszik a telefon: GitHub → Settings → Developer settings → Fine-grained tokens → a token neve → „Delete”.
- Leválasztás: Data fül → Sync → „**Disconnect**”. Ilyenkor az eszköz elfelejti a tokent, az adataid megmaradnak az eszközön és a repóban is.
- A szinkron csak a naplót, a saját ételeket, az Open Food Facts-ból elmentett ételeket, a saját adagokat és a NOVA-besorolásokat viszi át. A téma (Appearance) és a legutóbbi mennyiségek eszközönként külön maradnak.

## 10. Elemzés Claude-dal

A Data fülön a „**Daily totals (CSV)**” minden naphoz tartalmazza az összes tápanyagot. Az üres cella azt jelenti, hogy nincs adat. A `__max` végű oszlopok a „< x” értékek felső határát adják, a `__n` oszlopok pedig azt, hogy hány tételből van adat. Az „Entries (CSV)” ugyanezt tételenként mutatja: a `source` oszlop megmondja, honnan jön az étel (`ciqual`, `usda`, `off` vagy `user`), a `date` oszlop a nap, a `time` oszlop a tétel időpontja (óra:perc, 24 órás), a `nova` oszlop az étel NOVA-csoportja (1–4, üres, ha nincs besorolva), az `energy_estimated` oszlop azt mutatja, hogy a kalória számolt érték-e (1) vagy címkeadat (0), az `estimate_confidence` oszlop a becslés megbízhatósága (high, medium, low, very low, none): a dmBio termékeknél és azoknál a saját ételeidnél van kitöltve, amelyeknél becslést jelöltél (12. fejezet), az étkezés oszlopában „Meal 1”, „Meal 2” stb. áll. A régebbi tételeknél, amelyekhez még nem mentettünk időpontot, az app a felvétel pillanatát írja. A `__est` végű oszlopok azt jelölik, hogy az érték becslés: a tételes fájlban 1 = becsült, 0 = nem becsült, a napi összesítőben a becsült tételek száma. Ilyen oszlop csak azoknál a tápanyagoknál van, amelyek valamelyik tételnél tényleg becsültek (dmBio termék vagy `~` jelű érték egy saját ételben). Az „Entries (CSV)” `est_keys` oszlopa (az `estimate_confidence` után) felsorolja a tétel becsült tápanyagait, pontosvesszővel elválasztva (például `vitamin_e;zinc`). Ha a kalória is becsült, a `kcal` is ott áll. A „Daily totals (CSV)” `est_share` oszlopa (a `entries` után) azt mondja meg százalékban, hogy a nap értékeinek mekkora része becslés. Tápanyagonként kiszámolja, hogy a nap mennyiségének hányadrésze jön becsült értékből, majd ezeknek a hányadoknak az átlagát veszi azokon a tápanyagokon, amelyekhez van adat és a napi összeg nagyobb nullánál (egy tizedesjegyre kerekítve). 0 azt jelenti, hogy minden érték címkeadat, üres cella azt, hogy aznap egyetlen tápanyagról sincs adat. Töltsd fel valamelyiket egy beszélgetésbe vagy projektbe.

## 11. Hogyan frissítesz egy új verzióra

1. Csomagold ki az új zip-et.
2. Nyisd meg a repót a GitHubon, kattints az „Add file” gombra, majd az „Upload files” menüpontra.
3. Húzd be az új fájlokat. Az azonos nevűeket a GitHub felülírja.
4. „Commit changes”. Pár perc múlva az új verzió él.
5. A telefonon nyisd meg az appot, és nézd meg a Data fül alján az „App version” kártyát. Ha ott még a régi verziószám áll, koppints a „Reload app files” gombra (internet kell hozzá). Az adataid megmaradnak, csak az app fájljai töltődnek le újra.

## 12. Tétel felvétele AI-val („Paste from AI”)

Ez akkor jó, ha új terméket veszel fel, és a címkén csak néhány érték áll. Egy AI (Claude, ChatGPT vagy más) megkeresi a címkeadatokat, a hozzávalók listájából megbecsüli a hiányzókat (vitaminok, ásványi anyagok), és egy kész adatcsomagot (JSON) ad vissza. Az app ezt egy lépésben betölti **saját ételként**, de előtte te átnézed. Semmi nem mentődik, amíg nem koppintasz a „Save” gombra. Az app ehhez nem hív meg semmilyen internetes szolgáltatást, és a beillesztett szöveget nem tárolja el.

**Egyszer: másold ki az AI utasítását (a „promptot”).**
1. A My foods fülön koppints a „**Paste from AI**” gombra. (Ugyanez a gomb a „Log food” keresőablak alján is ott van, a „+ Create food from label” mellett.)
2. Koppints a „**Copy AI prompt**” gombra. Alul megjelenik, hogy „AI prompt copied”: az utasítás a vágólapodon van. Internet nélkül is működik, mert a prompt az app része.
3. Nyiss egy beszélgetést az AI-val, és illeszd be az utasítást. Ha Claude-ot használsz, a legkényelmesebb, ha a Projects részben a projekt utasításai vagy dokumentuma közé teszed, akkor nem kell minden alkalommal újra beilleszteni.
4. A becsléshez az AI-nak a `ciqual_ref.json` fájlra is szüksége van (CIQUAL 2020 referenciaértékek). Csatold az első üzenethez, vagy tedd a Claude-projekted dokumentumai közé (nálad ott van). Kell hozzá egy AI, amely kódot tud futtatni (Claude-ban a kódfuttatás legyen bekapcsolva). Ha a fájl nincs csatolva, az AI csak a címkén szereplő értékeket adja meg, becslés nélkül. Ez nem hiba, de a vitaminok és ásványi anyagok így hiányozni fognak.

**Minden új tételnél:**
1. Küldd el az AI-nak a terméket: a csomagolás és a tápérték-táblázat fotóját, vagy a nevét és vonalkódját, vagy egy linket. Ha az AI visszakérdez (például nem látszik a hozzávalók listája), válaszolj rá.
2. Az AI egy rövid összefoglalót és egy `json` blokkot ír. Másold ki a **teljes választ**. Az sem baj, ha körülötte szöveg van, vagy három fordított idézőjel (```) veszi körül: az app magától megtalálja benne az adatot. Az AI-appokban a válasz alatt van egy „Copy” gomb.
3. Nyisd meg a Nutrilogot: My foods fül → „**Paste from AI**”.
4. Koppints a „**Paste from clipboard**” gombra. Ha a telefon egy kis „**Paste**” buborékot mutat, koppints rá: az app azonnal beolvassa a szöveget.
   Ha a buborék nem jön fel, vagy az app azt írja, hogy „This browser did not let the app read the clipboard”: nyomd hosszan az „AI answer” mezőt, válaszd a „**Paste**” menüpontot, és koppints a „**Read**” gombra. Ez mindig működik.
5. Ha az app hibát talál, a mező alatt kiírja, mi a baj (például hiányzik a név, negatív szám áll egy értéknél, vagy a becsült tápanyagnak nincs értéke). Ilyenkor semmi nem töltődik be. Kérd meg az AI-t: „Javítsd, és csak a JSON blokkot küldd el újra.”
6. Ha minden rendben, megnyílik a „**Review imported food**” ablak, az értékekkel előre kitöltve. Legfelül egy keret mondja meg, hány érték jön a címkéről és hány becslés. Ha az app valami gyanúsat talál (például a kalória nem illik a fehérjéhez, szénhidráthoz és zsírhoz, vagy a cukor több, mint a szénhidrát), a „**Check these:**” lista felsorolja. Ezek nem hibák, az étel így is betölthető, de nézd meg őket a csomagoláson.
7. Hasonlítsd össze az értékeket a csomagolással. Átírhatsz bármit, mint egy sima „Create food” ablakban.
8. Koppints a „**Save**” gombra. Ha a „Log food” keresőből jöttél, az étel rögtön megnyílik az „Amount” ablakban.

**A becsült értékek jelzése.**
- A becsült tápanyag neve előtt `~` jel áll, és mellette egy kék `~` gomb. A címkéről jövő értéknél a gomb szürke. A gombra koppintva ki-be kapcsolhatod, hogy az érték becslés-e. Ha törölsz egy értéket, a jel is eltűnik.
- Az „**Estimates (optional)**” részben két mező van: az „**Estimate confidence**” azt mondja meg, mennyire megbízható a becslés (high, medium, low, very low, none), a „**May be fortified**” pedig azt, hogy a termék dúsított lehet (vitamint vagy ásványi anyagot adtak hozzá). Ha van becsült érték, a megbízhatóságot ki kell választani, különben az app a mező mellett szól.
- Mentés után a becslések ugyanúgy látszanak, mint a dmBio termékeknél: a Nutrients fülön az érték előtt `~` áll, a tápanyag sorára koppintva az „Estimate, not a label value” sor megmondja, melyik étel becsült és mennyire megbízható. Az „Amount” ablakban az „**Estimated values: 3 · confidence low**” sorra koppintva (a szám a becsült értékek darabszáma) látod, mely értékek becslések, a dúsítási figyelmeztetést és az AI megjegyzését (a „Notes” mező tartalmát). A CSV-ben az `estimate_confidence` és a `__est` oszlopok jelölik őket (10. fejezet).

**Több termék egyszerre.** Ha az AI-válaszban több termék van, az app a „**Review imported foods**” listát mutatja. Minden sornál két gomb van: a „**Review**” megnyitja a szerkesztőt (ott módosíthatsz, és a „Save” ment), a „**Save**” úgy menti az ételt, ahogy van. A kész sor mellett „Saved” felirat látszik. A „Done” gombbal zárod be a listát. Amit nem mentettél, az nem kerül sehová.

**Ha az étel már megvan.** Ha a vonalkód egyezik egy saját ételeddel (vagy egy Open Food Facts-ból elmentett ételeddel), vagy a név és a márka ugyanaz (a kis- és nagybetűt, az ékezetet és a szóközt nem számítja), az app megkérdezi, mit tegyen: „**Already in your foods**”.
- „**Update existing**”: ugyanaz az étel marad, az értékei lecserélődnek az újakra. Ezért **a naplóban a régi tételek is az új értékeket mutatják** (az ablak megmondja, hány tételről van szó). Alul 6 másodpercig ott van az „**Undo**” gomb, amely visszaállítja a régi állapotot. Ami az új válaszban nincs benne (például vonalkód vagy megjegyzés), azt az app megtartja a régiből, a régi becslések viszont az újakkal együtt cserélődnek.
- „**Save as new**”: mindkét étel megmarad, és a naplóban semmi nem változik.
- „**Cancel**”: semmi nem történik, a szerkesztő nyitva marad.
Ha a régi étel darabra (például „capsule”), az új grammra vonatkozik, és már van hozzá naplótétel, az „Update existing” szürke, mert a tételeket nem lehet átvinni. Ilyenkor a „Save as new” a megoldás.

**Amit érdemes tudnod:**
- Ha az AI egy italt 100 ml-re vonatkozó értékekkel és egy „100 ml” (100 g) adaggal ad meg, az app **ml-ben** nyitja meg, a „Review imported food” ablakban a „100 ml (counted as 100 g)” van kiválasztva. A régebben betöltött italokat az „Update existing” ugyanígy átállítja, ha újra betöltöd őket.
- Az AI hibázhat, vagy rossz forrásból dolgozhat. A `~` jelű értékek becslések, a címkeérték az, ami a csomagoláson áll. Mindig vesd össze a csomagolással.
- A kalóriát az AI-nak a címkéről kell átvennie. Ha az app ezt írja: „Energy is … kcal, but protein, carbohydrate and fat add up to …”, nézd meg a címkét: gyakran a rost vagy a cukoralkohol okozza az eltérést, de lehet elírás is.
- A „Paste from AI” kétféle választ ért: a régi `nutrilog_import` alakút, és az újabb, `"app": "tapnaplo"` és `"foods"` objektumot tartalmazó alakot, amelyben a `confidence` magyarul is állhat (`magas`, `közepes`, `alacsony`, `nagyon alacsony`, `nincs becslés`). A „Copy AI prompt” gomb a 16-os verziótól a **3.1-es utasítást** másolja, és az az újabb alakot adja. Az utóbbinál az app a fájlban szereplő azonosítót nem használja, a mentéskor új azonosítót kap az étel. Ha a beillesztett szöveg egy teljes mentés (naplóval együtt), az app erre külön figyelmeztet, és a „Restore from file” gombot ajánlja.
- Az „AI answer” mezőbe bármilyen, a prompttal kapott válasz jó. Ha az app azt írja, hogy „This answer is version … of the import format”, az AI egy másik prompt-változatot használt. Koppints újra a „Copy AI prompt” gombra, és az új utasítással kérd a választ.
- Hígított termékeknél (növényi ital, leves, shake) a 3.1-es utasítás a becslést a címke kalóriájához skálázza, mert a víz nem tartalmaz tápanyagot. A megjegyzésben ez áll: „Skálázás: ×0,04 a címke energiájához”. Ilyenkor a `water` (víz) értéket az AI nem becsüli. Ha a címkén nincs kalória, és a víz az első három hozzávaló között van, az AI egyáltalán nem becsül, mert a hígítás nem állapítható meg.
- A beillesztett szöveget az app nem menti el, csak az az étel marad meg, amit a „Save” gombbal elmentettél. A mentett étel a mentésfájlban és a szinkronban is ott van, a becslésekkel együtt.

## 13. Ételek betöltése fájlból („Import foods (JSON)”)

Ez akkor kell, ha egy fájlban **több kész étel** van (például az AI-tól vagy az artifactból kapott `foods` fájl), és ezeket egyszerre akarod betölteni, átnézés nélkül. A gomb **csak a My foods listához ad hozzá**, a naplódhoz nem nyúl. Egy tétel vagy a „Paste from AI” átnézéssel megy, ez a gyors, tömeges út.

**Mit olvas a fájlból?** Egy JSON-fájlt, amelynek tetején `"app": "tapnaplo"` áll, és van benne egy `foods` rész. A fájlban lévő `log` (napló) és `meta` részt **figyelmen kívül hagyja**, ezért egy teljes mentésfájlból is csak az ételeket veszi át. Csak a **saját ételeket** tölti be, vagyis azokat, amelyeknek az azonosítója `u:`-val kezdődik (ilyen az AI-prompt `u:ai-…` azonosítója). Az elmentett Open Food Facts-termékeket és minden más forrást kihagy, és megszámolja őket.

**Betöltés lépésről lépésre:**
1. Tedd a fájlt a telefonodra (Fájlok app, iCloud, vagy küldd el magadnak). Egy AI-választ úgy kapsz fájlba, hogy a `json` blokk tartalmát elmented `.json` kiterjesztéssel. Ha csak szövegként van meg, egyszerűbb a „Paste from AI” (12. fejezet).
2. Nyisd meg a **Data** fület, és a „Backup” kártyán koppints az „**Import foods (JSON)**” gombra. Ez a „Restore from file” mellett van.
3. Válaszd ki a fájlt.
4. Ha minden étel új és hibátlan, az app **rögtön betölti** őket, és alul megjelenik: „**Imported 3 foods**” egy „**Undo**” gombbal (6 másodpercig).
5. Ha valami figyelmet kér, megnyílik az „**Import foods**” ablak. Ebben látod, hány étel jön be, melyek vannak már meg, melyik bejegyzés hibás, és milyen értékeket érdemes utána ellenőrizned. Az alján:
   - „**Skip**”: a már meglévő ételeid maradnak, ahogy voltak, csak az új ételek kerülnek be. Ez az alapértelmezett, az első gomb.
   - „**Overwrite**”: a meglévő ételeid értékei lecserélődnek a fájlban lévőkre. Az étel azonosítója nem változik, ezért **a naplóban a régi tételek is az új értékeket mutatják**.
   - „**Cancel**”: semmi nem történik.
6. Kész. Ha mégsem ezt akartad, koppints az „**Undo**” gombra: az új ételek eltűnnek, a felülírt ételek visszakapják a régi értékeiket.

**Amit érdemes tudnod:**
- Semmi nem íródik felül kérdés nélkül. Ha egy azonosító már megvan, az app megkérdezi, hogy a „Skip” vagy az „Overwrite” kell.
- Ha egy meglévő étel darabra (például „capsule”), a fájlban lévő grammra vonatkozik (vagy fordítva), és a naplóban már használod, az „Overwrite” azt az ételt **nem** írja felül, mert a tételek mennyiségét nem lehet átvinni. Az ablak megmondja, melyikről van szó. Ilyenkor maradj a meglévő ételnél, vagy javítsd a fájlban az azonosítót.
- Az érvénytelen bejegyzést (nincs neve, hiányzik az alapja, az egyik érték nem szám, a becsült kulcsnak nincs értéke) az app kihagyja, és megszámolja: „… 2 invalid skipped”. Az ablakban az első öt hiba okát látod. Ha egyetlen étel sem érvényes, a gomb alatt piros hibaüzenet áll („No food could be imported”), és semmi nem változik.
- Ha a fájl nem Nutrilog-fájl, a gomb alatt ezt olvasod: „This is not a Nutrilog file…”. Ha a „Restore from file” gombbal próbálsz betölteni egy olyan fájlt, amelyben csak ételek vannak (napló nincs), az app ezt írja: „this file has foods but no diary” és az „Import foods (JSON)” gombot ajánlja.
- Az app figyelmeztet, ha egy új étel vonalkódja vagy neve és márkája egyezik egy meglévő ételével: ezeket külön ételként adja hozzá, a felesleget a My foods listán törölheted.
- A becsült értékek (`est`), a megbízhatóság (`confidence`) és a „dúsított” jelzés (`fortified`) bekerül az ételbe, és ugyanúgy látszik, mint a „Paste from AI” után: `~` jel a Nutrients fülön, az „Estimated values: N · confidence …” sor az „Amount” ablakban.
- A fájl tartalmát az app nem küldi el sehova, és nem tárolja.

## Ha elakadsz

| Mit látsz | Mit csinálj |
|---|---|
| A webcím „404”-et ad | Várj 10 percet, és ellenőrizd, hogy az `index.html` a repó főoldalán van-e, nem almappában. Ha almappában van, töltsd fel újra a fájlokat. |
| „The app could not start” | Az `index.html`-re duplán kattintva az app nem indul, mert tárhely kell hozzá. Nyisd meg a GitHub-címről. |
| Üres oldal vagy régi verzió | Data fül → „App version” kártya → „Reload app files”. Ha az app el sem indul, frissítsd az oldalt, vagy zárd be és nyisd meg újra. |
| A kamera nem indul | Engedélyezd a kamerát a telefon beállításaiban a böngészőnek. Addig is beírhatod a vonalkód számjegyeit a „Scan” ablakban. |
| A beolvasott szám nem egyezik a vonalkód alatt nyomtatott számmal | A kamera félreolvasta. Koppints újra a „Scan barcode” gombra, vagy írd be a számot kézzel. Ha az „Open Food Facts does not have barcode …” üzenetet látod, először ellenőrizd a számot a csomagon. |
| A szkenner sokáig keresi a kódot | Tartsd a telefont 10–20 cm-re, laposan. Túl közelről a kamera nem élesít. Világosabb helyen és a fényes fólia megdöntésével jobban megy. |
| Az „Amount” mezőre koppintva nem jön fel a billentyűzet | Koppints közvetlenül a számra. Ha így sem jön fel a billentyűzet, használd a gyorsgombokat (10 g, 30 g, 50 g…), és szólj nekem. |
| „Enter a time in 24-hour form, for example 13:45.” | A „Time (24 h)” mezőbe óra:perc kell, 00:00 és 23:59 között. Írd be számjegyekkel (pl. `0830`), a kettőspontot az app teszi be. |
| Koppintáskor az oldal ráközelít a mezőre | A 13-as verziótól ez nem fordulhat elő. Ha mégis, Data fül → „Reload app files”, mert régi fájlok maradtak a telefonon. Két ujjal továbbra is nagyíthatsz és kicsinyíthetsz. |
| „The USDA food data could not be loaded” a naplóban, vagy nincsenek USDA-találatok | Az `usda.json` fájl nem töltődött le. Kapcsold be az internetet, majd Data fül → „Reload app files”. Az USDA-tételek addig rejtve vannak, törölve nincsenek. |
| „The dmBio food data could not be loaded” a naplóban, vagy nincsenek dmBio-találatok | A `dmbio.json` fájl nem töltődött le. Kapcsold be az internetet, majd Data fül → „Reload app files”. A dmBio tételek addig rejtve vannak, törölve nincsenek. |
| A Nutrients fülön az „Unclassified” sor 100% | A NOVA-csoportot neked kell beállítanod: Nutrients fül → „Set NOVA groups” → koppints az 1–4 számokra az ételek mellett. A CIQUAL és USDA ételekhez nincs beépített besorolás. |
| „Open Food Facts does not have barcode…” | A termék nincs az adatbázisban. Használd a „Create food from label” gombot. |
| „Open Food Facts is not available right now” | Az adatbázis szervere éppen nem válaszol. Próbáld újra egy perc múlva. |
| „Could not reach Open Food Facts” | Ellenőrizd az internetet. Hiányos vagy hiányzó terméknél használd a „Create food” gombot. |
| „GitHub does not accept the token” | A token lejárt, vagy rosszul másoltad. Csinálj újat (9. fejezet, B), majd Data fül → Sync → „Disconnect” → „Set up sync”. |
| „the token needs the permission “Contents: Read and write”” | A tokenben a „Contents” nem „Read and write” értékű. Csinálj új tokent a B lépések szerint. |
| „This repository is public” | Az app csak privát repóhoz kapcsolódik. Csinálj egy újat a „Private” opcióval (9. fejezet, A). |
| „The file … is not a Nutrilog sync file” | A repóban van egy fájl az `entries/`, `foods/` mappában vagy `meta.json` néven, ami nem az appé. Használj külön, üres repót a Nutrilognak. |
| A Sync kártyán „Offline: your changes stay on this device…” | Nem hiba: nincs internet vagy a GitHub nem érhető el. A változások megmaradnak, és elmennek, amikor újra van kapcsolat. |
| „Another device keeps writing at the same time” | Két eszköz egyszerre szinkronizált. Várj egy percet, és koppints a „Sync now” gombra. |
| „No JSON found” a „Paste from AI” ablakban | A beillesztett szövegben nincs `nutrilog_import` adatblokk. Másold ki az AI teljes válaszát, a `json` blokkal együtt. Ha az AI nem adott ilyet, kérd: „Küldd el az eredményt a Nutrilog JSON formátumában.” |
| „This answer cannot be loaded” és egy lista a mező alatt | A lista megmondja, melyik érték hibás. Küldd el neki, és kérd: „Javítsd, és csak a JSON blokkot küldd el újra.” |
| „The answer has Nutrilog data, but it cannot be read as JSON” | A válasz vége hiányzik, mert az AI félbehagyta. Kérd, hogy küldje el újra csak a JSON blokkot. |
| „This browser did not let the app read the clipboard” | Nem hiba. Nyomd hosszan az „AI answer” mezőt, válaszd a „Paste” menüpontot, majd koppints a „Read” gombra. |
| „This answer is version … of the import format” | Az AI a régi (1-es) prompt-alakkal dolgozott, vagy ismeretlen verziót írt. A „Paste from AI” ablakban koppints a „Copy AI prompt” gombra, illeszd be az új utasítást, és kérd újra a választ. Ha az app a régebbi, Data fül → „Reload app files”. |
| „This is not a Nutrilog file” az „Import foods (JSON)” gomb alatt | A fájl tetején nincs `"app": "tapnaplo"`. Ellenőrizd, hogy a teljes JSON-t mentetted el, és ne a magyarázó szöveget. |
| „No food could be imported” az „Import foods (JSON)” gomb alatt | Egyetlen bejegyzés sem érvényes. Az üzenet az első okokat megmutatja (például hiányzó név vagy alap). Kérd az AI-t, hogy javítsa, és csak a JSON-t küldje el. Az azonosítónak `u:`-val kell kezdődnie. |
| „Could not restore: this file has foods but no diary” | A fájlban csak ételek vannak. A „Restore from file” teljes mentéshez való. Ételek betöltéséhez használd az „Import foods (JSON)” gombot (13. fejezet). |
| Eltűnt az adatom | Töltsd vissza a legutóbbi mentést: Data fül, „Restore from file”. Az app megerősítést kér, mielőtt felülírja az adataidat. |

## Amit érdemes tudnod

- Az általános élelmiszerek adatai a francia CIQUAL 2020 táblából jönnek (3186 étel, 64 tápanyag, francia piaci átlagok, angol nevekkel). A magyar termékeknél a legközelebbi megfelelőt kapod, a pontos érték a címkén van.
- Az USDA adatai az amerikai mezőgazdasági minisztérium FoodData Central adatbázisából jönnek: a Foundation Foods (2026. április, 436 étel) és az SR Legacy (2018, 7793 étel) táblából. Ezek amerikai piaci átlagok, szabadon felhasználható közkincsek. Amit az USDA nem mér, azt az app „nincs adat”-nak hagyja, nem nullának. Három dolgot számolunk: a sót a nátriumból (nátrium × 2,5), a nyers fehérjét a nitrogénből (× 6,25, csak a Foundation ételeknél), és a D-vitamint a nemzetközi egységből (IU × 0,025), ha csak az van megadva. A K2-vitamin az USDA-nál csak az MK-4 forma. A zsírsavaknál csak a pontosan azonosított értéket vettük át, ezért ott több a hiányzó adat. A Foundation táblában néhány étel azonos néven többször szerepel (több minta), ilyenkor az FDC szám különbözteti meg őket.
- A dmBio termékek (527 db, dm-drogerie markt Magyarország) be vannak építve az appba, a dm.hu termékoldalairól. Az energia és a makrók a dm tápértéktáblázatából jönnek (ahol a táblázat ellentmondott magának, a becslési projekt javította). Minden más érték **becslés** a hozzávalók listájából, a CIQUAL 2020 nyers alapanyagaival (dmBio becslés v3, 2026. október 24.). A becslés átlagérték, nem mérés: a „confidence” mutatja, mennyire bízhatsz benne. Ahol a dm.hu-n nincs táblázat, ott címkeérték sincs. A dmBio ételek NOVA-csoportja üres, azt te állítod be.
- A csomagolt termékek az Open Food Facts közösségi adatbázisból jönnek. A címkeadat hiányos vagy hibás lehet, ezért érdemes összevetni a csomagolással.
- Italoknál az app grammal számol, és 1 ml-t 1 g-nak vesz. Hígabb italoknál ez elég pontos. Ha egy saját ételnél a „100 ml (counted as 100 g)” van kiválasztva (a „Create food” és az „Edit food” ablakban, vagy az AI-válasz 100 ml-es adagja alapján magától), az app **ml-ben mutatja** a mennyiséget, a számolás ettől nem változik. A régebben felvett italok grammban maradnak, amíg az „Edit food” ablakban át nem állítod őket. A CSV `unit` oszlopában ilyenkor `ml` áll.
- Ez egy tájékoztató eszköz, nem orvosi tanács.

**Források:** Anses. 2020. Ciqual French food composition table, <https://doi.org/10.5281/zenodo.4770202> (CC BY 4.0). U.S. Department of Agriculture, Agricultural Research Service. FoodData Central, <https://fdc.nal.usda.gov> (U.S. public domain). dmBio termékek: dm-drogerie markt Magyarország termékoldalai, <https://www.dm.hu>; mikrotápanyag-becslés: dmBio becslés v3 (CIQUAL 2020 alapján). Open Food Facts, <https://world.openfoodfacts.org> (ODbL). Vonalkód-olvasó: ZXing-js (Apache 2.0, lásd `ZXING-LICENSE.txt`).
