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
   Az ablak közepén, a kalóriakártyában (a nagy „kcal” szám alatt) az „**All nutrients with data for this amount**” lista mutatja az étel **összes** makró- és mikrotápanyagát, **arra a mennyiségre kiszámolva, amit az „Amount” mezőbe írtál**. Ha átírod a számot, a lista azonnal követi. Csoportokba van rendezve, mint a Nutrients fülön (Energy & macronutrients, Minerals, Vitamins …). A `~` jel becsült értéket jelent, a `<3` pedig azt, hogy az érték a kimutatási határ alatt van (legfeljebb ennyi). Amihez az ételnek **nincs adata**, az nincs a listában, az app csak megszámolja őket („No data for 54 more nutrients”), és **nem nullának veszi** őket. Ugyanez a lista látszik, ha a Diary fülön egy már felvett tételre koppintasz („Edit entry”): ott a tétel mennyiségére számolja.
4. A találatok négy helyről jönnek, ebben a sorrendben: „dmBio (dm.hu products)” (a dm drogéria bio termékei, lásd alább), „CIQUAL (generic foods)” (francia átlagok), „USDA (generic foods, US)” (amerikai átlagok), végül az „Open Food Facts” (csomagolt termékek, ezt külön gombbal kéred). A saját ételeid, ha vannak, mindig legfelül állnak. Az USDA-ból először 10 találat látszik, a „**Show more USDA results**” gombbal újabbakat kapsz. Az USDA-soron a „SR Legacy” vagy „Foundation” felirat és egy „FDC” szám látszik: ez az USDA saját azonosítója, a fdc.nal.usda.gov oldalon rá tudsz keresni. Az USDA ételeknél az Amount ablakban gyorsgombok vannak a háztartási mértékekkel (például „1 large”, „1 cup, chopped”), a mennyiség viszont alapból 100 g marad.
5. A tétel megjelenik a naplóban, a neve alatt az időponttal (pl. `07:45 · 100 g · CIQUAL`). Egy étkezésen belül a tételek idő szerint követik egymást. Ha módosítani (a mennyiséget, az étkezést vagy az időpontot) vagy törölni akarod, koppints rá.
   Minden étkezés fejléce alatt egy sor mutatja az adott étkezés összegét grammban, rövidítésekkel: `P` fehérje (protein), `C` szénhidrát (carbohydrate), `F` zsír (fat), `Fib` rost (fibre) és `Salt` só. Például: `P 23g  C ≥30g  F ≥7.5g  Fib ≥3g  Salt ≥1.5g`. A `≥` azt jelenti, hogy az étkezés legalább egy tételéhez nincs megadva az adott érték, ezért az összeg csak alsó becslés (a hiányzó adat nem nulla). A `~` azt jelenti, hogy az érték egy része becslés, nem címkeérték. A `–` azt jelenti, hogy az étkezés egyik tételénél sincs adat. Az üres étkezés alatt nincs ilyen sor. A nap összege (a nagy kártya a Diary tetején) ettől független. A 21-es verziótól ugyanez a sor minden tétel alatt is megjelenik, de csak arra az egy tételre és az általad megadott mennyiségre számolva. Például egy 150 g-os tételnél: `P 15g  C 30g  F 7.5g  Fib 3g  Salt 1.5g`. A jelek ugyanazt jelentik: `~` becsült érték, `≥` alsó érték (például a címkén „<0,5 g” áll), `–` nincs adat. A tételre koppintva ugyanúgy megnyílik a szerkesztő, mint eddig. A 22-es verziótól a tétel `Salt` értéke **piros és félkövér**, ha az adott tétel (az általad megadott mennyiséggel) több, mint 0,4 g sót tartalmaz. Pontosan 0,4 g még nem piros, és az sem, ha a kijelzett érték 0,4 g. Becsült érték (`~`) is lehet piros. Az alsó értéknél (`≥`) a piros azt jelenti, hogy már a biztosan meglévő rész is 0,4 g fölött van. Ha egy tételnél a só nincs megadva (`Salt –`), ott nincs piros jelzés, akkor sem, ha a nátrium értéke ismert. Az étkezés-sor és a nap összege nem pirosodik. A határ (0,4 g) az app kódjában egy szám (`SALT_ALERT_G`), ha módosítani szeretnéd, szólj.

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

**Vízfogyasztás követése („Water intake”):**
A Diary fülön a makró-kártya alatt, a Meal 1 fölött van a „**Water intake**” kártya. Nagy számmal mutatja a nap összegét mL-ben (mellette dL-ben). **Minden vízfelvitel külön rögzül, időponttal** (34. verzió), ugyanúgy, mint az ételtételek.
1. Egy pohár vízhez koppints a „**+1 dL**”, „**+2 dL**”, „**+3 dL**” vagy „**+5 dL**” gombra. Az app a **mostani időponttal** rögzíti. Az összeg azonnal nő, alul pedig értesítés jelenik meg a mennyiséggel, az időponttal és a napi összeggel (például „Water +2 dL at 21:24 · total 200 mL”), az „**Undo**” gombbal, ha elnyomtad.
2. Más mennyiséghez, vagy ha korábban ittál, koppints az „**Other**” gombra. Az ablakban válaszd az „**mL**” vagy a „**dL**” lehetőséget (1 dL = 100 mL), és írd be a mennyiséget (a tizedest ponttal és vesszővel is, pl. `1,5`). A „**Time (24 h)**” mezőben az idő alapból a mostani. Ha korábban ittál, írd át: elég a számokat beírnod, a kettőspontot az app teszi ki (a `0715` `07:15` lesz). Végül koppints az „**Add …**” gombra: a gomb felirata megmondja, mennyit adsz hozzá. Az alatta lévő gyorsgombok kitöltik a mennyiség mezőt. Ha átváltasz mL-ről dL-re vagy vissza, az app átszámolja a beírt mennyiséget. A legutóbb használt mértékegységet az app megjegyzi ezen a telefonon.
3. **A felvitelek listája.** Ha a naphoz van felvitel, a kártyán ott áll a „**Recordings (3) · last 21:24**” sor. Koppints rá: kinyílik a lista időrendben, soronként az idővel és a mennyiséggel. A lista nyitva marad, amíg dolgozol vele.
4. **Javítás és törlés.** Koppints egy sorra: megnyílik az „**Edit water**” ablak. Itt átírhatod a mennyiséget és az időt, majd koppints a „**Save changes**” gombra. A „**Delete**” azonnal törli a felvitelt, és megjelenik az „Undo” gomb. Az idő átírása a felvitelt soha nem teszi át másik napra.
5. A „**Clear day**” az egész nap vizét törli (minden felvitelt), ez is visszavonható az „Undo” gombbal. A régi „Subtract” gomb megszűnt: levonás helyett javítsd vagy töröld a megfelelő felvitelt.
6. A nap a Diary tetején lévő nyilakkal vagy a naptárral váltható: minden napnak külön listája és összege van.
Egy napra legfeljebb 20 000 mL (200 dL) vihető fel.

**A 34. verzió előtt felvitt vized** nem veszett el. A régi napi összegek a listában „**No time**” soron látszanak, és beleszámítanak a napi összegbe. Az app nem találgat nekik időpontot. Rájuk koppintva a mennyiséget átírhatod vagy törölheted, időpontot nem lehet hozzájuk adni. Ha egy régi nap vizét időponttal akarod látni, töröld a „No time” sort, és vidd fel újra az „Other” gombbal a helyes idővel.

**Amit érdemes tudnod:** a „Water intake” csak azt számolja, amit te ide felvittél. Ha egy italt ételként veszel fel a „Log food” gombbal, az nem számít bele, mert az az étkezés része, és a Nutrients fülön a „Water” sorban látszik (az az ételeid víztartalma, nem az ivott víz). Ha egy napra semmit nem vittél fel, az app nem tekinti nullának: a „Daily totals (CSV)” üresen hagyja a cellát. A vízfogyasztás része a mentésnek, a Sync-nek és a megosztott linknek is, az időpontokkal együtt. A Report fül „Time of day” szakasza óránként megmutatja, mikor ittál (17. fejezet).

**Hogyan olvasd a Nutrients fület:**
- A `≥` jel azt jelenti: legalább ennyi. Hiányzó adatnál az összeg alsó becslés, mert az app a hiányt nem tekinti nullának.
- A jobb oldali jelvény (pl. `4/6`) azt mutatja, hogy a nap hat tételéből négyhez van adat az adott tápanyagról. A tápanyagra koppintva látod, melyik tételből hiányzik (lásd lejjebb).
- Ha egy tápanyag sorára koppintasz, először az „**Added up from**” lista nyílik le: azok az ételek, amelyekhez **van adat** az adott tápanyagról, a mennyiséggel, amit ettél, és azzal az értékkel, amelyet ez az étel a tápanyag összegéhez hozzátesz. A legtöbbet adó étel áll legelöl. Ha ugyanazt az ételt aznap többször vitted fel, egy sorban látod összevonva (például „200 g · 2 entries”). A sorok értékei adják ki a sor tetején látható összeget, a `<` és a `~` jel ugyanúgy érvényes bennük. Alatta jön a „No data for: …” sor azokról a tételekről, amelyekhez nincs adat. Ha senkihez nincs adat, a lista nincs ott, és a sor „no data” feliratot kap.
- A `~` jel az érték előtt azt jelzi, hogy az érték (egy része) **becslés**, nem címkeadat. Az energia előtt azt jelenti, hogy a kalóriát a fehérjéből, szénhidrátból és zsírból számolta ki az app. A dmBio termékeknél azt, hogy a tápanyagot a hozzávalók listájából becsülték. A saját ételeidnél azt, hogy te (vagy az AI-válasz) becslésnek jelölted az értéket. Koppints a tápanyag sorára: az „Estimate, not a label value” sor megmondja, melyik tételek becsültek, és mennyire megbízható a becslés.
- A **Water** (víz) az „Energy & macronutrients” csoportban van, az energia és a makrók mellett. A napi összegben az ételekből és italokból származó víz látszik. A víz nem számít bele a „tracked nutrients” számlálóba (az továbbra is 42 tápanyagot számol).
- A **Caffeine** (koffein, mg-ban) az „**Other components**” csoportban van, a lista legvégén. Ez a csoport alapból összecsukott: koppints a nevére. A sor ugyanúgy működik, mint a többi: `≥` jel és jelvény, ha nem minden tételhez van adat, „Added up from” lista, `~` a becsléseknél. **A koffeinadat nem minden ételhez van meg.** A CIQUAL táblában egyáltalán nincs koffein, a dmBio termékeknél sincs (azok becslése a CIQUAL-ból jön), ezeknél a sor „no data”-t vagy `≥` jelet mutat, és az app a hiányt **nem tekinti nullának**. Koffeinadatot ezekből kapsz: az **USDA** (SR Legacy) tábla a kávéhoz, teához, kólához, energiaitalhoz, étcsokoládéhoz és kakaóhoz megadja (7793 ételből 5215-nél van érték, ebből 289-nél nulla fölött), az **Open Food Facts** termékeknél akkor, ha a közösségi adat tartalmazza, és a **saját ételeid**, ha beírod („Create food” → „More values” → „Other components” → „Caffeine”). Pontos kávé- vagy teaértékhez ezért az USDA-s tételt vedd fel (például „Beverages, coffee, brewed”: 40 mg 100 g-ban, vagyis egy 250 g-os csésze 100 mg), ne a CIQUAL-t. Ajánlott napi értéket az app nem mutat a koffeinhez (az EFSA-értékek táblája, 16. fejezet, nem tartalmaz koffeint). Az AI-prompt (12. fejezet) a 36-os verziótól (3.2-es utasítás) kéri a koffeint: csak akkor ír be értéket, ha a csomagon vagy a forrásban kifejezetten szerepel. Összetevőből (kávé, tea, guarana) nem következtet rá, a „koffeinmentes” felirat önmagában nem nulla, és a koffeint soha nem becsüli.
- Az „**Omega-6 : omega-3 ratio**” sor a „Fatty acids & cholesterol” csoportban van, a DHA (és ha beállítottad a referenciaértékeket, az „EPA + DHA” sor) alatt, a Cholesterol fölött. Ezt az app **számolja ki** a nap összegeiből: az omega-6 a linolsav (Linoleic acid) és az arachidonsav (Arachidonic acid) összege, az omega-3 az alfa-linolénsav (Alpha-linolenic acid), az EPA és a DHA összege, és a kettő hányadosa látszik, például `0.21 : 1`. Az app **nem mutat célértéket** az arányhoz, és nincs hozzá sáv sem. A sorra koppintva látod a két összeget, és azt, melyik zsírsavból mennyi került bele.
  - A hiányzó adatot az app **nem tekinti nullának**. Ha egy étel valamelyik zsírsavról nem tartalmaz adatot (például a növényi olajokhoz többnyire nincs arachidonsav, EPA és DHA adat), azt a zsírsavat kihagyja, és az arány elé `≈` jelet tesz („körülbelül”: a meglévő értékekből számolt arány). A koppintás után a „No data for: …” sor megmondja, melyik étel melyik zsírsavából hiányzik adat. Ha minden tételhez megvan mind az öt zsírsav, nincs `≈` jel.
  - A `~` jel az arány előtt azt jelenti, hogy az összeg egy része becslés. Ha az omega-3 csak „kisebb mint x” értékekből áll, az arány `≥` vagy tartomány (például `0–2 : 1`) lesz.
  - Ha az omega-6-hoz vagy az omega-3-hoz egyáltalán nincs adat, a sor „no data” feliratot kap. Ha az omega-3 adatban 0, vagy minden érték csak felső korlát, az arány „not defined”, mert nullával nem lehet osztani.
  - A sor csak a Nutrients fülön látszik, a CSV-ben és az Amount ablakban nincs.

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
3. Heti egy mentés elég. A mentésben benne vannak a naplóbejegyzések, a saját ételeid, a NOVA-besorolásaid, a vízfogyasztásod (az időpontjaival együtt) és a Health log jegyzeteid is. Mivel a jegyzetek egészségügyi adatok, a mentésfájlt csak olyan helyre tedd, ahová te egyedül férsz hozzá. Visszatöltés: Data fül, „Restore from file”. Ha a mentésfájl még a 34. verzió előtt készült, a visszatöltés a már felvitt, időpontos vízfelviteleidet nem törli, csak a régi, időpont nélküli napi összegeket cseréli le.
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
- A repóban fájlok vannak: `entries/ÉÉÉÉ-HH.json` (havonta egy, a naplóbejegyzéseiddel), `foods/` (saját ételek), `water/ÉÉÉÉ.json` (a 34. verzió előtti, időpont nélküli napi vízösszegek, évente egy fájl), `intake/ÉÉÉÉ-HH.json` (a vízfelvitelek időponttal, havonta egy fájl, a felvitel hónapja szerint), `health/ÉÉÉÉ-HH.json` (a Health log jegyzetei, havonta egy fájl, a jegyzet felvételének hónapja szerint), `ref/profile.json` (az ajánlott bevitel beállításai, 16. fejezet) és `meta.json` (saját adagok, NOVA-besorolások). Ezeket ne szerkeszd kézzel. A GitHubon a „History” gombbal visszanézheted a korábbi állapotokat.
- A token csak azon az eszközön van, ahol beírtad. Nem része a mentésfájlnak, és nem kerül a repóba. **Ne küldd el senkinek, nekem se, és képernyőképen se mutasd meg.** Ha elveszik a telefon: GitHub → Settings → Developer settings → Fine-grained tokens → a token neve → „Delete”.
- Leválasztás: Data fül → Sync → „**Disconnect**”. Ilyenkor az eszköz elfelejti a tokent, az adataid megmaradnak az eszközön és a repóban is.
- A szinkron csak a naplót, a saját ételeket, az Open Food Facts-ból elmentett ételeket, a saját adagokat, a NOVA-besorolásokat, a vízfogyasztást, a Health log jegyzeteit és az ajánlott bevitel beállításait viszi át. A jegyzeteid tehát a **saját privát repódba** is felkerülnek, ezért legyen a repó tényleg privát (az app amúgy sem csatlakozik nyilvános repóhoz). Az ajánlott bevitel beállításai abból látszanak, hogy terhes vagy-e, vagy szoptatsz-e (16. fejezet), ezért ez is csak a privát repóba megy. A téma (Appearance) és a legutóbbi mennyiségek eszközönként külön maradnak.

## 10. Elemzés Claude-dal

A Data fülön a „**Daily totals (CSV)**” minden naphoz tartalmazza az összes tápanyagot, a `water_intake_ml` oszlopban pedig az aznap ivott víz mennyiségét milliliterben (a „Water intake” kártyáról). Az a nap is kap sort, amelyiken csak vizet vittél fel. Az üres cella azt jelenti, hogy nincs adat (a `water_intake_ml` üres, ha aznapra nem vittél fel vizet, nem 0). A `water_intake_ml` az egész nap vize, az időpontos és az időpont nélküli régi összeg együtt. A „**Water intake (CSV)**” (34. verzió) a vízfelvitelek listája, soronként egy felvitel, a legrégebbivel kezdve: `date`, `time` (óra:perc, 24 órás) és `water_ml`. A régi, időpont nélküli összegeknél a `time` üres. A `__max` végű oszlopok a „< x” értékek felső határát adják, a `__n` oszlopok pedig azt, hogy hány tételből van adat. Az „Entries (CSV)” ugyanezt tételenként mutatja: a `source` oszlop megmondja, honnan jön az étel (`ciqual`, `usda`, `off` vagy `user`), a `date` oszlop a nap, a `time` oszlop a tétel időpontja (óra:perc, 24 órás), a `nova` oszlop az étel NOVA-csoportja (1–4, üres, ha nincs besorolva), az `energy_estimated` oszlop azt mutatja, hogy a kalória számolt érték-e (1) vagy címkeadat (0), az `estimate_confidence` oszlop a becslés megbízhatósága (high, medium, low, very low, none): a dmBio termékeknél és azoknál a saját ételeidnél van kitöltve, amelyeknél becslést jelöltél (12. fejezet), az étkezés oszlopában „Meal 1”, „Meal 2” stb. áll. A régebbi tételeknél, amelyekhez még nem mentettünk időpontot, az app a felvétel pillanatát írja. A `__est` végű oszlopok azt jelölik, hogy az érték becslés: a tételes fájlban 1 = becsült, 0 = nem becsült, a napi összesítőben a becsült tételek száma. Ilyen oszlop csak azoknál a tápanyagoknál van, amelyek valamelyik tételnél tényleg becsültek (dmBio termék vagy `~` jelű érték egy saját ételben). Az „Entries (CSV)” `est_keys` oszlopa (az `estimate_confidence` után) felsorolja a tétel becsült tápanyagait, pontosvesszővel elválasztva (például `vitamin_e;zinc`). Ha a kalória is becsült, a `kcal` is ott áll. A „Daily totals (CSV)” `est_share` oszlopa (a `entries` után) azt mondja meg százalékban, hogy a nap értékeinek mekkora része becslés. Tápanyagonként kiszámolja, hogy a nap mennyiségének hányadrésze jön becsült értékből, majd ezeknek a hányadoknak az átlagát veszi azokon a tápanyagokon, amelyekhez van adat és a napi összeg nagyobb nullánál (egy tizedesjegyre kerekítve). 0 azt jelenti, hogy minden érték címkeadat, üres cella azt, hogy aznap egyetlen tápanyagról sincs adat. A „**Health log (CSV)**” a Health log jegyzeteit adja, külön fájlban (15. fejezet): a `date` oszlop alapján összekapcsolhatod a két étkezési fájllal. Töltsd fel valamelyiket egy beszélgetésbe vagy projektbe.

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
- A 3.2-es utasítás (36-os verzió) három dolgot pontosít. **Koffein:** a `caffeine` kulcs (mg) csak címkeértékből kerülhet be, becslésből soha. **Alkohol:** ha a címke térfogatszázalékot (% vol) ad, az AI 100 ml-re a g-ot × 0,789-cel számolja ki (az etanol sűrűsége), és ezt megírja a megjegyzésben. **Folyadékok sűrűsége:** ha a címke 100 ml-re adja az értékeket, azok változatlanul maradnak (az app 1 ml = 1 g-mal számol, ezért ml-ben mérve pontos, olajnál és méznél is). Ha 100 g-ra adja, és az ital nem víz alapú (olaj, méz, szirup, ecet, szósz), az AI csak ismert sűrűségnél ad „100 ml” adagot (például méz: 142 g), különben nem. Az ismert sűrűségek: víz 1,00; tej 1,03; napraforgóolaj és repceolaj 0,92; olívaolaj 0,91; méz 1,42; háztartási ecet 1,01. A napraforgóolaj értékét kevesebb forrás támasztja alá, mint a többit.
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

## 14. A napló megosztása a dietetikussal („Share diary and nutrients”)

Ezzel egy **linket** csinálsz, amely a kiválasztott napok **Diary**, **Nutrients** és **Report** fülét mutatja, **csak olvasható** formában. Aki megnyitja (például a dietetikusod), mindent lát úgy, ahogy te: a tételeket, a P / C / F / Fib / Salt sorokat, a piros sót, a `~`, `≥` és `–` jeleket, a NOVA-kártyát és a tápanyag-sorokat. Hozzáadni, átírni vagy törölni nem tud semmit.

**Hogyan működik, és mit kell tudnod róla?** A kiválasztott napok adatai **magában a linkben** vannak (a cím végén a `#share=` utáni hosszú rész). Semmi nem töltődik fel sehova, nincs szerver, és a te döntésed szerint **nincs jelszó** sem. Ebből két dolog következik:
- **Aki megkapja a linket, látja a napokat.** Csak annak küldd el, akinek szánod.
- **A linket nem lehet visszavonni, és pillanatfelvétel.** Ha utána új tételt veszel fel vagy átírsz egyet, az nincs benne. Az új állapothoz új linket kell csinálnod.

**Link készítése lépésről lépésre:**
1. Nyisd meg a **Data** fület, és keresd meg a „**Share diary and nutrients**” kártyát.
2. Koppints a kártyán a „**Share diary and nutrients**” gombra.
3. Válaszd ki az időszakot: „**7 days**”, „**14 days**” vagy „**30 days**” (a mai napig számolva), vagy állítsd be a „**From**” és a „**To**” dátumot kézzel (legfeljebb 62 nap).
4. Az ablak megmondja, hány napról és hány tételről van szó, és milyen hosszú a link. Ha van vízfelvitel is, azt is kiírja (például „water intake on 3 days (with times)”). Ha a kiválasztott napokban nincs tétel, azt írja, és nem ad linket.
5. Koppints a „**Share link**” gombra: megnyílik a telefon megosztó ablaka, ahonnan elküldheted a dietetikusnak (e-mail, üzenet…). Ha a böngésződ nem tud megosztani, csak a „**Copy link**” gomb van: koppints rá, a link a vágólapra kerül („Link copied”), és te illeszted be az üzenetbe.
6. Ha a böngésző nem engedi a másolást, egy mező jelenik meg a linkkel. Nyomd hosszan a mezőt, válaszd a „**Select All**”, majd a „**Copy**” menüpontot.

**Hosszú link.** Hét nap jellemzően néhány ezer karakter. Ha a link 4000 karakternél hosszabb, az ablak figyelmeztet: néhány csevegőapp levágja a nagyon hosszú üzeneteket (a Telegram például 4096 karakternél), és akkor a link nem nyílik meg. Válassz kevesebb napot, vagy küldd e-mailben.

**Ajánlott bevitel a linkben.** Ha beállítottad az ajánlott bevitelt a Nutrients fülön (16. fejezet), a megosztó ablakban megjelenik az „**Include reference intake settings**” jelölőnégyzet, alapból bepipálva. Ilyenkor a dietetikus is látja a sávokat és a százalékokat, ugyanazokkal a számokkal, mint te. A beállításokból az is kiderül, hogy terhes vagy-e, vagy szoptatsz-e. Ha ezt nem akarod elküldeni, vedd ki a pipát: a link rövidebb lesz, és semmit nem tartalmaz a beállításaidról. A linket utólag sem lehet visszavonni, ezért a küldés előtt döntsd el.

**Mit lát a dietetikus?**
- A linket telefonon vagy számítógépen, bármelyik böngészőben megnyithatja. Nem kell appot telepítenie és fiókot csinálnia.
- Felül egy „**Shared diary · read-only**” megjegyzés áll az időszakkal és a készítés idejével.
- Csak három fül van: **Diary**, **Nutrients** és **Report**. A Diary és a Nutrients fülön a nyilakkal és a naptár gombbal lépked a megosztott napok között, a többi napra nem.
- A **Report** fülön (17. fejezet) a megosztott napokból állít össze időszakot. Alapból az egész megosztott tartományt mutatja („Custom”). A „Week” és a „Month” a megosztott napokra van levágva, és ezt ki is írja („shared days only”). A „3 months”, „6 months” és „Year” gomb szürke, ha a link legfeljebb 62 napot tartalmaz, mert ahhoz hosszabb időszak kell.
- Nincs „Log food”, nincs „+” gomb, a tétel megérintésére nem nyílik meg semmi, és a NOVA-csoportokat sem lehet beállítani.
- Ha a megosztott napokon van vízfogyasztás, a Diary fülön ott van a „**Water intake**” kártya is, gombok nélkül. A „Recordings” listában ott vannak a felvitelek időpontjai is, de nem lehet őket szerkeszteni (a 34. verzió előtt felvitt, időpont nélküli összeg „No time” soron áll). Ha egy napra nem vittél fel vizet, azt írja: „Not logged”. Olyan linken, amelyik nem tartalmaz vizet, a kártya nem látszik. Egy napon, amelyen csak vizet vittél fel, étel nélkül is lehet linket készíteni.
- Az app **nem ír semmit** az ő böngészőjének tárhelyébe, és ha neki is van saját Nutrilog-naplója ugyanezen a címen, ahhoz **nem nyúl**.
- Az első megnyitáskor a böngésző letölti az ételtáblákat. Az USDA- és a dmBio-táblát csak akkor, ha a megosztott napokban van ilyen étel.

**Mi van a linkben?** A tételek (nap, étkezés, időpont, mennyiség) és azoknak az ételeknek az értékei, amelyeket te hoztál létre vagy mentettél el az Open Food Facts-ból (a becslésjelölés, a megbízhatóság, a „dúsított” jelzés és a NOVA-csoport is). A megjegyzés (`note`), a vonalkód és az adagok **nem** kerülnek bele. A **Health log jegyzetei sem**: a link soha nem tartalmaz egészségnapló-jegyzetet, a megosztott nézetben nincs is Health log fül, és a megosztó ablak ki is írja („Health log notes are not included in the link.”). A CIQUAL, USDA és dmBio ételek csak azonosítóval szerepelnek, az értéküket az app a saját táblájából veszi, ezért ha egy tábla később frissül, a régi link már az új értékeket mutathatja.

## 15. Egészségnapló („Health log”)

A Health log egy általános egészségnapló az étkezési napló mellett: rövid, időbélyeges jegyzeteket írhatsz benne mindarról, ami az egészségeddel kapcsolatos, napi, heti vagy havi gyakorisággal. **Nem része az étkezési adatoknak.** Egyetlen kalória- vagy tápanyagösszegbe sem számít bele, a Diary és a Nutrients fül nem változik tőle.

**Jegyzet felvétele:**
1. Koppints az alsó sávban a „**Health log**” fülre (a „My foods” és a „Data” között van).
2. Koppints a kerek „**Add note**” gombra.
3. Válaszd ki a címkét. „**Symptom**”: hogyan érzed magad. „**Event**”: valami történt, például új kiegészítőt kezdtél szedni. „**Observation**”: valamit észrevettél. Pontosan egyet kell választanod. Az app nem jelöl ki előre egyet, hogy véletlenül se kerüljön rossz címke egy jegyzetre.
4. Írd be a szöveget a „**Note**” mezőbe. Legfeljebb **1000 karakter** lehet (az ékezetes betű és az emoji is egy karakter). A mező alatti számláló mutatja, hol tartasz („0 / 1000”). Az Enter új sort ír. Az app **semmit nem vág le csendben**: ha túllépted a határt, hibaüzenetet kapsz („The note can be 1,000 characters at most. It is 1,042 characters now.”), és a jegyzet addig nem mentődik, amíg meg nem rövidíted.
5. A „**Date**” és a „**Time (24 h)**” mező alapból a pillanatnyi nap és idő. Átírhatod, ha a jegyzet egy korábbi napra vonatkozik, például egy heti összefoglalónál. Jövőbeli nap nem adható meg. Az időt számokkal írd: a `1745` magától `17:45` lesz, 24 órás formában.
6. Koppints a „**Save note**” gombra. Az app megerősíti: „Note added”.

**A lista.** Időrendben mutatja a jegyzeteket, a legújabb van legfelül. Minden sorban ott van a dátum és az idő, a címke (szóval kiírva, nem csak színnel) és a szöveg első 100 karaktere. A sortöréseket és a többszörös szóközöket egy szóközzé alakítja, és „…” jelzi, ha a jegyzet hosszabb. Egyszerre 100 sort mutat. Ha több jegyzeted van, a lista alján a „**Show older notes**” gomb betölti a következő 100-at. A lista fölött a jegyzetek száma látszik.

**Teljes jegyzet, szerkesztés, törlés:**
1. Koppints egy sorra. Megnyílik a jegyzet a teljes szöveggel, a sortörésekkel együtt.
2. „**Edit**”: ugyanaz az ablak nyílik meg „Edit note” címmel, a mentett értékekkel. A „**Save changes**” után a jegyzetnél megjelenik az „Edited …” sor, amelyik azt mutatja, mikor szerkesztetted utoljára. A jegyzet eredeti felvételi ideje nem változik. A „Note updated” üzenet „**Undo**” gombja visszaállítja a régi változatot. Ha nem módosítottál semmit, a mentés nem számít szerkesztésnek.
3. „**Delete**”: a jegyzet azonnal törlődik, megerősítő kérdés nélkül. A „Note deleted” üzenet „**Undo**” gombja néhány másodpercig visszahozza.

**Vázlat.** Ha elkezdesz egy új jegyzetet, és mentés nélkül bezárod az ablakot (az X-szel vagy a „**Cancel**” gombbal), a szöveg és a címke **vázlatként megmarad ezen a telefonon**. A következő „Add note” ablakban a „Draft restored” sor jelzi, hogy visszatöltődött. A dátum és az idő ilyenkor a pillanatnyi lesz. A „**Discard draft**” gombbal eldobhatod, a mentés pedig magától törli. Szerkesztésnél nincs vázlat. A vázlat csak azon a készüléken van, nem része a mentésnek és a szinkronnak.

**Mi van még a jegyzetekkel:**
- **Mentés (JSON):** a mentésfájlban benne vannak (a `health` rész). Aki a fájlt látja, az egészségügyi jegyzeteidet is látja. A „Restore from file” a `health` résszel rendelkező fájlnál **lecseréli** a jegyzeteidet, és a megerősítő ablak kiírja, hány jegyzetet tölt vissza. A 25-ös verzió előtt készült mentésben nincs `health` rész: azt visszatöltve a jegyzeteid érintetlenek maradnak. Ha a fájlban hibás jegyzet van, az app kihagyja, és megmondja, hányat.
- **Szinkron:** ha bekapcsoltad (9. fejezet), a jegyzeteid a saját privát repódba kerülnek (`health/ÉÉÉÉ-HH.json`). Ha ugyanazt a jegyzetet két eszközön módosítod, a későbbi módosítás nyer, a jegyzet egészében (szövegrészeket nem fésül össze). A régebbi (24-es) app ezt a mappát figyelmen kívül hagyja, tehát nem törli és nem írja felül a jegyzeteket.
- **CSV:** Data fül → „**Health log (CSV)**”. Egy sor egy jegyzet, a legrégebbi elöl: `date`, `time`, `label` (`symptom`, `event` vagy `observation`), `note` és `edited` (az utolsó szerkesztés ideje `ÉÉÉÉ-HH-NN óó:pp` alakban, üres, ha nem szerkesztetted). A `date` oszlop alapján összekapcsolhatod az étkezési fájlokkal, például egy Claude-beszélgetésben.
- **Megosztó link:** a jegyzetek **nincsenek benne** a dietetikusnak szánt linkben (14. fejezet).
- Keresés és szűrés címke szerint egyelőre nincs.

## 16. Ajánlott napi bevitel a Nutrients fülön („Reference intake”)

A Nutrients fülön a mikrotápanyagok sorai alatt megmutathatja az app, hogy a mai beviteled hány százaléka az **EFSA** (az Európai Élelmiszerbiztonsági Hatóság) felnőttekre megadott ajánlott értékének. Ehhez nem kell semmit felvinned az ételeken kívül, csak egyszer megadni, melyik csoportba tartozol.

**Beállítás lépésről lépésre:**
1. Koppints az alsó sávban a „**Nutrients**” fülre. Legfelül a „**Reference intake**” kártyát látod.
2. Koppints a „**Male**” vagy a „**Female**” gombra. Ez egy koppintással beállítja a leggyakoribb választ: 25 év felett, a nőknél a menopauza előtt, a cinknél a 600-as szint. A sávok azonnal megjelennek. Az „**Undo**” gomb visszavonja.
3. Ha ettől eltérsz (terhes vagy, szoptatsz, 25 évnél fiatalabb vagy, a menopauza után vagy), koppints a kártyán a „**Change**” gombra.
4. Az ablakban válassz: „**Sex**” (Male, Female, Pregnant, Nursing), „**Age**” (18–24 vagy 25 and over), nőknél „**Menopause**” (Not yet vagy Past), és a „**Zinc: phytate in your diet**” sort. A cinkből azért kell ez, mert a teljes kiőrlésű gabona és a hüvelyesek csökkentik a felszívódását. Ha nem tudod, hagyd a 600-on.
5. Koppints a „**Save**” gombra. A „**Cancel**” gomb mindent úgy hagy, ahogy volt. A „**Remove settings**” gomb (az ablak tartalmában, piros) kikapcsolja az egészet, és az „Undo” visszahozza.

**Mit látsz?** Minden olyan sor alatt, amelyikhez az EFSA ad értéket, egy vékony sáv és egy sor áll, például: „≥ 77% of 950 mg · PRI”. A sor végén a típus:
- **PRI** (Population Reference Intake): az az érték, amely az egészséges felnőttek mintegy 97,5%-ának igényét fedezi. Tömör sáv.
- **AI** (Adequate Intake): ahol az EFSA nem tudott PRI-t megállapítani, mert kevés volt a bizonyíték. Ez azon alapul, mennyit esznek az egészséges emberek. **Szaggatott sáv.** A gyengébb alapú AI-soroknál (magnézium, réz, mangán, E-vitamin, B5-vitamin) a megnyitott sor ki is írja: „Staying below this is not a deficiency.”
- **SAI** (safe and adequate intake): a nátriumnál és a kloridnál. **Pontozott sáv.** Ez nem cél, amit el kell érni, a legtöbb európai felnőtt többet eszik.

A sáv 100%-nál megáll, a szám tovább nő. Egyetlen szín sem „ítél”: a 20% és a 300% ugyanolyan kék, nincs piros vagy zöld. A túl magas bevitelre vonatkozó felső határokat (UL) az app még nem mutatja.

**A hiányzó adatot az app nem veszi nullának.** Ugyanazok a jelek, mint máshol:
- „**≥ 50%**”: valamelyik tételnél nincs adat erről a tápanyagról, ezért ez alsó érték.
- „**~10%**”: az érték egy része becslés.
- „**0–20%**”: egy „<x” értékből jön, az alsó és a felső határ látszik.
- „**no data to compare**” és nincs sáv: aznap egyik tételnél sincs adat. Soha nem látsz „0%”-ot adat nélkül. A valódi nulla (például 0 mg kalcium egy tételen) viszont 0%.

**Néhány sor másképp számol:**
- **Vitamin A**: az EFSA retinol-egyenértékben (RE) adja meg. Az app a retinolt és a béta-karotin hatodát adja össze („with beta-carotene”). A többi karotinoidról nincs adat, ezért ez szigorúan véve alsó érték (a megnyitott sor ezt ki is írja). A „≥” jel akkor jelenik meg, ha valamelyik tételnél a retinol vagy a béta-karotin hiányzik.
- **Vitamin B1 (thiamin)** és **Vitamin B3 (niacin)**: az EFSA ezeket a nap energiájához köti (B1: 0,1 mg, niacin: 1,6 mg NE megajoule-onként). Az app csak akkor számol százalékot, ha **minden** tételnél van energiaadat, különben azt írja: „needs complete energy data”. A niacin mindig alsó érték, mert a triptofánból is képződik niacin, és erről nincs adatunk.
- **Folate**: terhességben az EFSA csak AI-t ad (600 µg DFE), egyébként PRI-t.
- **Kalcium** (18–24 évesen 1000, utána 950 mg), **vas** (menopauza előtti nőknek, terhesnek és szoptatónak 16, másnak 11 mg), **cink** (a fitáttól függ).
- **EPA + DHA**: ez egy új, számolt sor a DHA alatt (csak beállított profilnál). Az EPA és a DHA összege grammból milligrammra átváltva; az EFSA ajánlása 250 mg, terhesen és szoptatva az app 350 mg-ot használ (250 mg és a legalacsonyabb pótlás: 100 mg).
- **Fibre** (rost): 25 g (AI).

**Fontos tudnivalók:**
- Az ajánlott értékek **hosszú távú napi átlagok**. Egyetlen nap, amelyik alatta marad, nem hiány. A kártya ezt ki is írja.
- 18 év alattiaknak az app nem mutat értéket, mert az EFSA-nak ott más a táblázata.
- Ez tájékoztató, nem orvosi vagy dietetikai tanács. Ha terhes vagy, szoptatsz, vagy betegség miatt más a szükségleted, a dietetikusod értékei mérvadók.
- A „**About reference intakes**” lenyíló részben (a kártyán) a PRI, az AI és az SAI magyarázata és a forrás van.
- A kártyán a **jelmagyarázat** (32. verzió) megmondja, mit jelent a folytonos, a szaggatott és a pontozott sáv: folytonos = PRI, szaggatott = AI, pontozott = SAI (ez nem cél). Csak azok a fajták szerepelnek benne, amelyekből az adott napon vagy időszakban tényleg van sáv a soroknál. Alatta áll: a sáv 100%-nál megáll, a mellette lévő százalék tovább megy. Ha nincs sáv (nincs beállítás, üres nap, vagy nincs olyan tápanyag, amelyiknek van értéke és adata), jelmagyarázat sincs.

**Mit tárol az app a beállításokból?** Csak a választásaidat (Sex, Age, Menopause, Zinc), a **korodat vagy a születési dátumodat nem**.
- **A telefonon**, és a mentésfájlban (JSON, `meta.ref`). A „Restore from file” a fájlban lévő beállításokra cserél. Ha a mentés a 26-os verzió előtt készült (nincs benne beállítás), a te beállításaid megmaradnak, és a megerősítő ablak ezt kiírja. Ha a fájlban sérült beállítás van, az app kihagyja, és megmondja.
- **Szinkron:** ha bekapcsoltad (9. fejezet), a beállítások a saját privát repódba kerülnek (`ref/profile.json`). Mivel kiderül belőlük, hogy terhes vagy-e, vagy szoptatsz-e, tényleg csak privát repóba mehetnek.
- **Megosztó link:** csak akkor, ha az „Include reference intake settings” be van pipálva (14. fejezet).
- **CSV:** a két CSV-fájl nem változik, nincs bennük referenciaoszlop.

**Amit nem tudtam ellenőrizni.** Két adat a megvalósításkor nem volt kéznél az eredeti dokumentumból:
1. A **nátrium** 2000 mg-os értéke az EFSA 2019-es véleményéből való. Magát a véleményt nem tudtam megnyitni, a kloridnál ezt az EFSA kivonata és egy ellenpróba megerősítette (2,0 g nátrium = 87 mmol; ennyi kloridion 3,1 g).
2. A CIQUAL „vitamin E” oszlopáról nem tudom, α-tokoferol vagy α-tokoferol-ekvivalens (α-TE). Az EFSA értéke mindkettőre épül, ezért a sor megjegyzést kap. A különbség általában kicsi, de ha pontosság kell, a címkén lévő értéket nézd.

## 17. Riport több napra („Report”)

A Nutrients fül egy napot mutat. A **Report** fül ugyanazokat a számokat adja **egy hétre, egy hónapra vagy akár egy évre**: átlagot naponta, az EFSA-sávokat az átlagra, és azt is, mennyire bízhatsz a számokban. Az alsó sávban a Nutrients és a My foods között van.

**Időszak kiválasztása lépésről lépésre:**
1. Koppints az alsó sávban a „**Report**” fülre.
2. A tetején a „**Day**”, „**Week**”, „**Month**”, „**3 months**”, „**6 months**”, „**Year**” és „**Custom**” gombok közül válaszd ki az időszak hosszát. Az app emlékszik rá, a következő megnyitáskor ugyanaz lesz kiválasztva (csak ezen a telefonon, nem kerül a mentésbe és a Syncbe).
3. A két nyíllal lépsz az előző vagy a következő időszakra. A naptár ikonnal megadhatod azt a napot, amely köré az időszak épül. Ha elmentél a mai időszaktól, megjelenik a „**Today**” gomb, ami visszaugrik.
4. A „**Custom**” gomb megnyit egy ablakot: a „**From**” és a „**To**” mezőbe írd be az első és az utolsó napot, vagy koppints a „**Last 14 days**”, a „**Last 30 days**” vagy a „**Whole diary**” gombra. Az „**Apply**” gomb elfogadja, a „**Cancel**” mindent úgy hagy. Hibát (például a kezdő nap a vég után van, vagy a vég a jövőben) a mező alatt látsz.

**Hogyan számol az app az időszakokkal?**
- A **hét hétfőn kezdődik**. A „Month” a naptári hónap, a „3 months” az adott hónap és az előtte lévő két hónap, a „6 months” az adott hónap és az előtte lévő öt, a „Year” az adott hónap és az előtte lévő tizenegy.
- Ha az időszak még nem ért véget (például a mai hét), a **mai napig** tart, és a fejlécben ott áll: „so far”.
- Egy nap akkor számít **naplózott napnak**, ha van legalább egy tétele. Az üres napokat az app **kihagyja**, nem számolja nullának. Ha egy héten három napot vittél fel, az átlag a három napé, nem a hété.

**Mit mutat a nyolc rész?** Az „Overview”, a „Trend”, a „Nutrients”, a „Meals and weekdays”, a „Foods”, a „Food processing (NOVA)”, a „Data quality” és a „Time of day” szakaszt a címére koppintva nyithatod és zárhatod. Az app megjegyzi, melyik van nyitva (csak ezen a telefonon).
- **Overview:** a naponkénti átlag kcal-ban nagy számmal (az „Average per logged day” felirat alatt), alatta a fehérje, szénhidrát, zsír, rost, cukor és só átlaga, és a vízfogyasztás átlaga. A vizet csak azokból a napokból átlagolja, amelyeken felvittél vizet. A „**Days**” szakasz napokra bontva mutatja az energiát. Egy napos időszaknál itt van az „**Open in Diary**” gomb is, ami a Diary fülön megnyitja azt a napot.
- **Trend:** egyetlen mértéket (alapból az energiát) mutat oszlopokban, hogy lásd, hogyan alakult az időszak alatt. Részletesen lejjebb olvasod („Trend: oszlopdiagram az időszakról”). Egyetlen napos időszaknál nincs Trend, mert nincs mit összehasonlítani.
- **Nutrients:** a Nutrients fül sorai az időszak átlagával. A sor megnyitva megmutatja, melyik ételekből jön az érték („Added up from”), hol nincs adat, és ha beállítottad az ajánlott bevitelt (16. fejezet), az EFSA-sávot az **átlagra** számolja. Egyetlen napos időszaknál a számok megegyeznek a Nutrients fülével.
- **Meals and weekdays:** melyik étkezésnél és a hét melyik napján eszel többet (lejjebb: „Meals and weekdays”).
- **Foods:** mely ételekből jön a kiválasztott mérték (alapból az energia). A Trenddel közös a mérték (lejjebb: „Foods”).
- **Food processing (NOVA):** az időszak energiájának megoszlása NOVA-csoportonként, és ennek alakulása oszloponként (lejjebb: „Food processing (NOVA)”).
- **Data quality:** melyik napokon van tétel (kitöltött nap), hol van víz (pont), mekkora része becsült érték, honnan jön az energia (CIQUAL, USDA, dmBio, saját étel), és mely tápanyagokról van a legkevesebb adat.

**A jelek jelentése (ugyanaz, mint a Nutrients fülön):**
- `≥` az érték előtt: legalább egy tételnél hiányzik az adat, ezért a valódi átlag **nagyobb is lehet**. A hiányzó adat soha nem nulla.
- `~`: az érték egy része becslés, nem címkeérték.
- `0–20`-féle tartomány: a „<x” értékekből jön.
- „no data”: az időszak egyik tételénél sincs adat. Sáv és százalék ilyenkor nincs.
- A sor végén a **százalék** azt mutatja, a tételek hány százalékánál van adat az adott tápanyagról (100%, ha mindegyiknél; 0%, ha egyiknél sem; <1%, ha az 1 százaléknál kevesebb, de nem nulla).
- Az **átlag alsó határ**: ha egy naplózott napon nincs adat egy tápanyagról, az a nap 0-val szerepel az összegben, de az osztóban is ott van a nap. Így a szám soha nem túloz. Ha egy időszak több napján nem mindenhol volt adat, a megnyitott sor megmutatja, hány napon volt teljes adat („Days with complete data”), és az ezekből számolt átlagot is.
- A B1-vitamin és a niacin az EFSA szerint a nap energiájától függ. Itt csak azokat a napokat veszi, amelyeken minden tételnél van energiaadat.

**Trend: oszlopdiagram az időszakról.** Az „Overview” alatti „Trend” szakasz egy mértéket mutat oszlopokban: egy oszlop egy nap (legfeljebb 31 napos időszaknál), egy hét (legfeljebb 190 napnál, hétfőtől vasárnapig) vagy egy hónap (hosszabb időszaknál). Egy hét- vagy hónap-oszlop értéke a benne lévő **naplózott napok átlaga**. Az időszak szélén a hét vagy a hónap lerövidülhet.

**Lépésről lépésre:**
1. A Report fülön koppints a „**Trend**” szakasz címére, hogy kinyisd.
2. A diagram fölötti gombon áll, melyik mértéket látod (alapból „**Energy**”). Koppints rá: megnyílik a „**Trend measure**” ablak. Felül a „Calculated” csoportban van a „Water intake” és az „Omega-6 : omega-3 ratio”, alatta a Nutrients fül csoportjai. Koppints arra, amelyiket látni szeretnéd, az ablak bezárul. A „**Close**” gomb változtatás nélkül zárja be. Ahol az időszakban egyik tételnél sincs adat egy tápanyagról, ott a neve mellett „no data” áll. Az app megjegyzi a választást (csak ezen a telefonon, nem kerül a mentésbe, a Syncbe és a megosztott linkbe).
3. Koppints egy oszlopra, vagy húzd végig az ujjadat a diagramon. A diagram alatt szavakkal olvasod a kijelölt oszlopot, például „Wed, 4 Nov · 150 kcal · 2 items”. A „**Previous bar**” és a „**Next bar**” nyíl is léptet. Induláskor az utolsó olyan oszlop van kijelölve, amelyben van tétel.
4. Az „**Open day**” gomb (hét-oszlopnál „**Open week**”, hónap-oszlopnál „**Open month**”) a kijelölt oszlopot teszi a Report időszakává. Így a diagramról egy koppintással a részletekhez jutsz.
5. A „**Show as table**” megnyitja az összes oszlop értékét táblázatban (nap vagy hét vagy hónap, érték, naplózott napok, tételek).

**Az oszlopok jelentése** (a diagram alatt a „jelmagyarázat” csak azokat sorolja fel, amelyek tényleg láthatók):
- **Tele oszlop:** minden tételnél van adat.
- **Csíkos oszlop:** alsó határ, a számnál `≥` áll. Valamelyik tételnél hiányzik az adat, ezért a valódi érték nagyobb is lehet.
- **Körvonalas, világos tető:** tartomány, a „<x” értékekből. A tető a felső határig ér.
- **Szaggatott alap, oszlop nélkül:** abban a napban, hétben vagy hónapban nincs tétel (a víznél: nincs felvitt víz). Ez **nem nulla**, csak üres.
- **Pontozott csonk:** van tétel, de egyiknél sincs adat erről a mértékről. Ez sem nulla.
- **Vízszintes vonal:** az EFSA ajánlott bevitele (16. fejezet), ha beállítottad, és a kiválasztott tápanyagnak van saját EFSA-értéke. Folytonos vonal a PRI-nél, szaggatott az AI-nál, pontozott a SAI-nál (nátrium és klorid, ez nem cél). Az oszlop a vonal alatt nem hiányt jelent. Az A-vitaminhoz, a B1-vitaminhoz és a niacinhoz nincs vonal, mert az EFSA azokat más egységben, illetve az energiához mérve adja meg. A vonal színe nem ítélkezik.
- **Víz:** a víz-oszlop azoknak a napoknak az átlaga, amelyeken felvittél vizet, mL-ben.
- **Omega-6 : omega-3 ratio:** a napok összegeiből számolt arány. A `≈` jel azt jelenti, hogy csak azokból a zsírsavakból számolta, amelyekről van adat (28. verzió).

**Megosztott linken** a Trend is működik, a megosztott napokból. A mérték és az időszak ott sem íródik sehová.

**Meals and weekdays: mikor eszel többet.** Három kártya van benne, mind az **energiát** mutatja kcal-ban:
- **Energy by meal:** a Meal 1 – Meal 6 étkezések egy naplózott napra eső átlaga, mellette az étkezés **százaléka** az ismert energiából (a százalékok összege 100), és egy sáv. A sor alatt áll, hány napon és hány tétellel számol („3 of 3 days · 3 items”). **Egy étkezés üres napja nullának számít:** ha a Meal 2-nél a hét három napjából csak egyen volt tétel, a másik két nap 0 kcal az átlagban, mert ott tényleg nem ettél semmit. Ezért a hat étkezés átlaga **összeadva az Overview átlagát adja**. Ha egy tételnek nincs energiaadata, az **nem nulla**: a szám elé `≥` kerül (csíkos sáv), és ha az étkezés egyetlen tételének sincs energiaadata, a sorban „no energy data” áll, százalék és sáv nélkül (pontozott vonal). Ahol az étkezésnél egyetlen napon sincs tétel, „no entries” áll (szaggatott vonal). A „No meal” sor régi adatot fog meg, amelynek az étkezése nem a Meal 1 – 6 egyike: így semmi nem vész el az összegből.
- **Energy by weekday:** a hét minden napjára (hétfővel kezdve) az azon a napon naplózott napok átlaga, a sor alatt a „1 logged day” vagy „3 logged days”. Ha az időszakban nincs ilyen hétköznap, „no logged day” áll: ez nem nulla, csak üres. Kevés napnál **egyetlen nap is sokat mozdít** az átlagon, ezért nézd a napok számát.
- **Weekdays and weekend:** a hétfő–péntek és a szombat–vasárnap átlaga egymás mellett.
Egy napos időszaknál (Day) a hétköznap-rész helyett ez áll: „Weekday averages need at least two logged days in the period.”

**Foods: mely ételekből jön az érték.** Megmutatja, melyik **ételek** adják a kiválasztott mérték (alapból az energia) legnagyobb részét az időszakban. Egy étel az időszak **összes tétele összeadva**: a sorban látod a mennyiséget, hány napon és hány tételben szerepelt („300 g · 2 days · 2 entries”), az értékét és a **százalékát** a listában szereplő ételek összegéből (a százalékok összege 100).

**Lépésről lépésre:**
1. A Report fülön koppints a „**Foods**” szakasz címére.
2. A lista fölötti gombon áll, melyik mértéket látod (alapból „**Energy**”). Koppints rá, megnyílik a „**Measure**” ablak. Válassz egy tápanyagot, az ablak bezárul. A „**Close**” gomb változtatás nélkül zárja be.
3. A **Trend ugyanazt a mértéket használja**: ha az egyiknél átváltod, a másik is követi. Az app megjegyzi (csak ezen a telefonon, nem kerül a mentésbe, a Syncbe és a megosztott linkbe).
4. A lista legfeljebb **10 ételt** mutat, a többi „**N more foods**” sorban van együtt. Alatta áll az „All foods with data” összeg.
5. Ha egy étel adata hiányzik erről a mértékről, a „**No data for:**” sor névvel megmondja. Ezek **nincsenek a listában és a százalékban**, és nem nullák. Ha az időszak egyik ételénél sincs adat, a lista helyett ez áll: „… so there is nothing to list. This is not zero.”

Három különlegesség: a **vízfogyasztásnak** és az **omega-6 : omega-3 aránynak** nincs étellistája (a víz egész napra felvitt összeg, az arány több zsírsav összegéből számolt szám), ezeknél a lista helyett egy mondat mondja meg, mit válassz helyette. Ha egy étel értéke csak „<x”-ként ismert, a sora `<x`-et mutat, **százalék helyett „–”-t kap**, mert az alsó határa 0, a valódi része sokkal nagyobb is lehet. A `~` és a tartomány (például „~195–396”) ugyanúgy értendő, mint a Nutrients fülön.

**Food processing (NOVA): mennyire feldolgozott az, amit eszel.** Felül egy kártya az időszak energiájának megoszlásáról NOVA 1 – 4 és „Unclassified” (besorolatlan) szerint, ugyanúgy, mint a Nutrients fülön. A százalék az **egész időszak összes tételéből együtt** készül (nem a napi százalékok átlaga), és csak azok a tételek számítanak, amelyeknél van energiaadat (a kártya alján áll, hány tételt hagy ki). Az 1 százaléknál kisebb rész „<1%”, nem 0%. A csoportokat **itt nem állíthatod**, csak olvasod őket: ha egy étel „Unclassified”, a kártya alján a hint megmondja, hogy a **Nutrients** fülön a „**Set NOVA groups**” alatt tudod besorolni.
Ha az időszak legalább két napos, alatta az „**Over time**” kártya: **egy sáv egy nap** (legfeljebb 31 napos időszaknál), **egy hét** vagy **egy hónap**, benne a NOVA-csoportok színei (ugyanazok, mint fent, mindegyik szegmensnek vékony körvonala van, hogy a világos színek is látsszanak). A sáv jobb oldalán a **NOVA 4**, az ultrafeldolgozott ételek aránya áll. Hét- és hónap-sávnál a százalék a benne lévő naplózott napokra szól, a név alatt áll, hány napról. Ahol nincs tétel, szaggatott vonal áll „no entries” felirattal (ez nem 0%), ahol nincs energiaadat, pontozott vonal. A „**Show as table**” táblázatban is megadja ugyanezt (Day vagy Week vagy Month, NOVA 1, 2, 3, 4 és „No group”).

**Jelmagyarázat mindenhol, ahol sáv van (32. verzió).** A Trend alatt már eddig is állt, mostantól a **Meals and weekdays**, a **Foods** és a **Food processing (NOVA)** „Over time” kártyája alatt is ott van, ugyanolyan stílusban, és a Nutrients fül sávjaihoz is van (16. fejezet). Mindig **csak azokat a jeleket sorolja fel, amelyek az adott kártyán tényleg látszanak**, vagyis nincs benne csíkos jel, ha nincs csíkos sáv. A jelek kicsiben ugyanazok a sávok, mint a kártyán:
- **Teli sáv:** minden tételnek van energiaadata. A hossza az étkezésnél az ismert energiából vett rész, a hétköznapoknál a lista legmagasabb átlagához mért arány, a Foods-nál az étel része az összegből.
- **Csíkos sáv:** alsó érték (`≥`), valamelyik tételnél nincs energiaadat.
- **Szaggatott vonal:** nincs tétel („no entries”, „no logged day”). Ez nem nulla.
- **Pontozott vonal:** van tétel, de egyiknek sincs adata. Ez sem nulla.
- **Üres sáv** (Foods): nincs mit rajzolni, mert az érték 0, vagy csak „<x”-ként ismert.
- **Színes négyzet** (NOVA „Over time”): a sávokban látható NOVA-csoportok színe, csak az szerepel, amelyik tényleg van valamelyik sávban.
A megosztott linken ugyanezek a jelmagyarázatok jelennek meg. A „Meals and weekdays” kártyán **három** van: az étkezések, a hétköznapok és a hétfő–péntek / szombat–vasárnap sávjai alatt, mert mindegyiknél másképp mérjük a hosszt.

**Time of day: mikor eszel és iszol (33. és 34. verzió).** A Report utolsó szakasza, két kártyával, és egy harmadikkal, ha az időszakban van vízfelvitel. Nem tárol semmi újat, a már felvitt tételek és vízfelvitelek időpontjából számol.

- **When you eat:** a naplózott napokra az **átlagos első** és az **átlagos utolsó** tétel időpontja, a kettő közti **átlagos ablak** (például „9 h 25 min”), továbbá a **legkorábbi első** és a **legkésőbbi utolsó** tétel a napjával együtt. Egy napos időszaknál, vagy ha az időszakban csak egy naplózott nap van, csak a „First entry”, a „Last entry” és a „Window” sor áll ott. Az ablak az első és az utolsó tétel között eltelt idő, egyetlen tételnél 0 min.
- **Energy by hour:** 24 sáv, egy sáv egy óra (00:00-tól 23:59-ig). A sáv magassága az abban az órában elfogyasztott energia **naponkénti átlaga**. Ha egy naplózott napon abban az órában nem volt tétel, az az óra arra a napra 0 kcal, mert tényleg nem ettél semmit. A hiányzó adat viszont **soha nem nulla**: ha egy tételnek nincs energiaadata, a sáv csíkos és `≥` jelet kap, ha az órában csak ilyen tétel van, pontozott vonal áll ott („no energy data”). A 24 sáv összege ezért pontosan az Overview átlagos energiája (tesztelve).
- **Water by hour (34. verzió):** ugyanilyen 24 sáv a vízfelvitelekből. Egy sáv az abban az órában ivott víz **naponkénti átlaga mL-ben**, azoknak a napoknak az átlaga, amelyeken van időponttal rögzített vízfelvitel. Ha egy ilyen napon abban az órában nem ittál (nem volt felvitel), az az óra arra a napra 0 mL, mert nem ittál semmit. A 24 sáv összege ezért az ilyen napok átlagos vízmennyisége (tesztelve). A **34. verzió előtt felvitt, időpont nélküli összegeknek nincs órájuk**, ezért nincsenek a sávokban. A kártya megmondja, mennyi az (például „600 mL on 1 day was logged before water recordings had a time”). Ha az időszakban csak ilyen régi összeg van, azt írja: „No water in this period has a time.” Az olvasó sor szavakkal mondja az értéket: „07:00–07:59 · 375 mL · 2 of 2 days · 3 recordings”. A kártya akkor is ott van, ha az időszakban nincs étel, csak víz. Ha az időszakban nincs víz, a kártya nincs ott. A „Show as table” gomb a 24 órát táblázatban adja (Hour, Water, Days, Recordings). A jelmagyarázat két jelet ismer: tömör sáv (abban az órában ivott víz) és szaggatott alap (nincs felvitel, ez nem nulla).

**Egy óra értékének leolvasása lépésről lépésre:**
1. Koppints a Report fülön a „**Time of day**” szakasz címére.
2. Koppints egy sávra, vagy húzd végig az ujjadat a diagramon. A sáv alatti sor szavakkal mondja meg az értéket, például „12:00–12:59 · ≥ 100 kcal · 3 of 3 days · 3 items”. Induláskor a legmagasabb óra van kijelölve.
3. A sor két oldalán lévő nyilakkal óráról órára léphetsz (képernyőolvasónak „Previous hour” és „Next hour”).
4. A „**Show as table**” gomb mind a 24 órát táblázatban mutatja, napok és tételek számával.

**Fontos tudni az időpontról.** Az app azt az időt használja, amit a tételnél beállítottál (Diary → tétel → „Time (24 h)”). Ha nem módosítottad, az az idő, amikor felvitted a tételt: ha este írod be a reggelit, a Report a felvitel idejét mutatja, nem az evését. Ha egy tételnél javítod az időt, a Report követi. Az **éjfél utáni** tétel arra a napra kerül, amelyiken felvitted (a 00:20-as tétel az adott nap legkorábbi tétele, nem az előző éjszakáé). Ha egy tételnek nincs használható ideje (nagyon régi mentésben fordulhat elő), az innen **kimarad**, és a kártya megmondja, hány ilyen van. Az „Energy by hour” csak az energiát mutatja, nem választható mérték. A „Water by hour” mindig mL-t mutat.

A diagram alatt ugyanolyan jelmagyarázat áll, mint a Trendnél, és csak azokat a jeleket sorolja fel, amelyek a diagramon látszanak. A megosztott linken (14. fejezet) ez a szakasz is ott van, ugyanazokkal a számokkal, a vízfelvitelek időpontjával együtt.

**Ha az időszakban nincs tétel**, egy kártya közli ezt („No entries on …” vagy „No entries from … to …”), és a „**Go to Diary**” gombbal átugorhatsz a naplóba. Ha egy tétel ételének adatát nem sikerült betölteni (például az USDA-tábla hiányzik), a fejléc alatt figyelmeztető sor mondja meg, hány tételt nem számolt az app.

**Megosztás.** A megosztott linken (14. fejezet) a Report fül a harmadik fül, és csak a megosztott napokat látja, a Trenddel, a „Meals and weekdays”, a „Foods”, a „Food processing (NOVA)” és a „Time of day” szakasszal együtt. A „Foods” mértékét ott is választhatod, de írni ott sem tud semmit, és a NOVA-csoportot sem tudja beállítani.

## 18. Változatosság („Variety”): az előkészület, még nem látszik a Report fülön

Ez a fejezet egy **készülő** funkcióról szól. A cél az, hogy az app megmondja, hány *különböző* növényi és állati egységet ettél egy héten (például hányféle zöldséget). A funkció lépésenként épül, és minden lépés külön verzió. A Report fülön a Variety szakasz **még nincs kész**, ezért a használatodban egyelőre semmi sem változik.

**Mi van kész:**
- **37-es verzió:** a rögzített lista. 17 főcsoportból, 75 alcsoportból és 164 egységből áll (például zöldség › levélzöldség › spenót). Az app induláskor ellenőrzi.
- **38-as verzió:** egy saját tétel (amit te vittél fel, vagy az Open Food Facts-ból mentettél el) három új, **elhagyható** mezőt kaphat: a **csoportot** (a lista egy alcsoportja vagy egysége), a csoport **eredetét** (honnan jött: automatikus javaslatból, kézzel vagy AI válaszából) és egy **jelölőt** (most csak a „belsőség”, vagyis az „offal”, és csak a hús csoportjain belül).

**Mit jelent ez neked most:**
- Semmit nem kell megadnod. A tétel felvételénél, az „Edit food” ablakban és a naplózásnál nincs új mező vagy gomb. Egy csoport nélküli tétel egyszerűen „besorolatlan”.
- Az új mezők **egyelőre csak az AI-s betöltésen át érkezhetnek**: ha a „Paste from AI” vagy az „Import foods (JSON)” válasza tartalmaz egy `vt` mezőt, az app megnézi, szerepel-e a listán. Ha igen, a tétel megkapja. Ha nem szerepel, vagy hibás az alakja, a mező **kimarad**, a „Check these:” sorban elolvashatod, miért, és a tétel ettől még betöltődik. Az app semmit nem javít át és nem talál ki.
- Ami már megvan a tételen, azt az „Edit food”, az „Update existing” és a mentés megőrzi. Ha az „Update existing” válasza nem tartalmaz csoportot, a régi marad. Ha tartalmaz, az felváltja a régit.
- A mezők **elmennek** a mentésfájlba (Save backup), visszaállításkor visszajönnek, a Sync átviszi őket a másik eszközre, a megosztó link is tartalmazza őket (a linkformátum nem változott), a „**Entries (CSV)**” pedig három új oszlopot kap a `nova` után: `variety_unit`, `variety_source`, `variety_flags`. Az üres cella azt jelenti, hogy a tétel nincs besorolva.
- Régi mentésfájl, régi Sync-adat és régi link változtatás nélkül működik.
- A tárolt adatból vagy a mentésfájlból érkező hibás alakú csoportot az app **eldobja**, a tétel megmarad, és szól, hány tételt érintett. A Sync-ből érkező hibás csoportot szó nélkül dobja el. Egy hibátlan, de az app listájában nem szereplő azonosítót (például egy későbbi lista egységét) **megtartja**, és besorolatlannak számolja.

**Hogyan nézheted meg, hogy a lista betöltődött:**
1. Nyisd meg a **Data** fület.
2. Görgess le a „**Sources & licences**” kártyához.
3. Keresd a mondatot: „Variety list: 164 units in 17 groups.” Ha az app nem tudta betölteni, a mondat ezt írja, az okával együtt, a többi funkció ettől még működik.

**Ami még nincs meg:**
- A CIQUAL, USDA és dmBio tételeknek még nincs csoportjuk (javaslati fájlok jönnek hozzájuk, jóváhagyott sorokkal).
- A csoportot beállító képernyő (hasonló a „Set NOVA groups”-hoz).
- Az AI-prompt frissítése a csoport azonosítóival.
- A Report fül „Variety” szakasza.

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
| A Nutrients fülön nincsenek sávok és százalékok | Nincs beállítva az ajánlott bevitel. Nutrients fül → „Reference intake” kártya → „Male” vagy „Female” (16. fejezet). Az étel nélküli napon csak a kártya látszik. |
| Egy sor alatt „no data to compare” áll sáv nélkül | Aznap egyik tételnél sincs adat arról a tápanyagról. Nem nulla, csak hiányzik. |
| A B1- vagy B3-vitamin sorában „needs complete energy data” áll | Ezeket az EFSA a nap energiájához köti, és az app csak akkor számol, ha minden tételnél van energiaadat. Írd be a hiányzó kalóriát a tételnél (vagy a saját ételnél). |
| „The file … is not a Nutrilog sync file” | A repóban van egy fájl az `entries/`, `foods/`, `water/`, `health/`, `ref/` mappában vagy `meta.json` néven, ami nem az appé. Használj külön, üres repót a Nutrilognak. |
| A Sync kártyán „Offline: your changes stay on this device…” | Nem hiba: nincs internet vagy a GitHub nem érhető el. A változások megmaradnak, és elmennek, amikor újra van kapcsolat. |
| „Another device keeps writing at the same time” | Két eszköz egyszerre szinkronizált. Várj egy percet, és koppints a „Sync now” gombra. |
| „No JSON found” a „Paste from AI” ablakban | A beillesztett szövegben nincs `nutrilog_import` adatblokk. Másold ki az AI teljes válaszát, a `json` blokkal együtt. Ha az AI nem adott ilyet, kérd: „Küldd el az eredményt a Nutrilog JSON formátumában.” |
| „This answer cannot be loaded” és egy lista a mező alatt | A lista megmondja, melyik érték hibás. Küldd el neki, és kérd: „Javítsd, és csak a JSON blokkot küldd el újra.” |
| „The answer has Nutrilog data, but it cannot be read as JSON. Often its end is missing…” | A válasz vége hiányzik, mert az AI félbehagyta. Kérd, hogy küldje el újra csak a JSON blokkot. |
| „…cannot be read as JSON: … The problem is at ⟨here⟩ in …” | A válasz teljes, de egy ponton hibás az írása (például hiányzó érték, vagy tizedesvessző a szám helyén: `0,65` a `0.65` helyett). A `⟨here⟩` jel pontosan megmutatja, hol akadt el az app. Másold ki ezt a mondatot, küldd el az AI-nak, és kérd: „Javítsd, és csak a JSON blokkot küldd el újra.” Ami nem hiba: a megjegyzésben (`note`) lévő idézőjel, az új sor, a felesleges záró `}` és a vessző a lista végén. Ezeket az app 20-as verziója óta elfogadja. |
| „This browser did not let the app read the clipboard” | Nem hiba. Nyomd hosszan az „AI answer” mezőt, válaszd a „Paste” menüpontot, majd koppints a „Read” gombra. |
| „This answer is version … of the import format” | Az AI a régi (1-es) prompt-alakkal dolgozott, vagy ismeretlen verziót írt. A „Paste from AI” ablakban koppints a „Copy AI prompt” gombra, illeszd be az új utasítást, és kérd újra a választ. Ha az app a régebbi, Data fül → „Reload app files”. |
| „This is not a Nutrilog file” az „Import foods (JSON)” gomb alatt | A fájl tetején nincs `"app": "tapnaplo"`. Ellenőrizd, hogy a teljes JSON-t mentetted el, és ne a magyarázó szöveget. |
| „No food could be imported” az „Import foods (JSON)” gomb alatt | Egyetlen bejegyzés sem érvényes. Az üzenet az első okokat megmutatja (például hiányzó név vagy alap). Kérd az AI-t, hogy javítsa, és csak a JSON-t küldje el. Az azonosítónak `u:`-val kell kezdődnie. |
| „Could not restore: this file has foods but no diary” | A fájlban csak ételek vannak. A „Restore from file” teljes mentéshez való. Ételek betöltéséhez használd az „Import foods (JSON)” gombot (13. fejezet). |
| „This link cannot be opened” (a dietetikus látja) | A link sérült vagy csonka: a csevegőapp levághatta, vagy egy extra karaktert tett a végére. Küldd el újra, hosszú linknél e-mailben, vagy válassz kevesebb napot. |
| „This link needs a newer version” | A link újabb Nutrilog-verzióval készült, mint amit a böngésző mutat. Töltse újra az oldalt egyszer (a „Reload page” gombbal, vagy telefonon húzza le az oldalt), és nyissa meg újra a linket. |
| „This browser cannot open the link” | Túl régi böngésző. Nyissa meg a linket a Chrome, a Safari vagy az Edge friss verziójában. |
| „The note can be 1,000 characters at most. It is N characters now.” | A jegyzet túl hosszú. Rövidítsd 1000 karakterre vagy kevesebbre. A mező alatti számláló („1100 / 1000 · 100 characters too many”) megmondja, mennyivel. |
| „The date cannot be in the future.” | A jegyzet napja csak a mai vagy egy korábbi nap lehet. |
| „N Health log notes could not be read and were skipped.” (induláskor) | A telefon tárhelyében sérült jegyzet volt, az app kihagyta. A többi megmaradt. Ha van friss mentésed, a „Restore from file” visszahozza a jegyzeteket. |
| A Trend helyén azt írja: „A trend needs at least two days with entries in this period.” | Az időszakban csak egy naplózott nap van, egyetlen oszlopból nem látszik alakulás. Válassz hosszabb időszakot a „Week”, a „Month” vagy a „Custom” gombbal, vagy vigyél fel több napot. A víznél két olyan nap kell, amelyen felvittél vizet. |
| „No item in this period has data for …” a Trend helyén | Az időszak egyik tételénél sincs adat arról a tápanyagról, ezért nincs mit rajzolni. Ez nem nulla. Válassz másik mértéket: a „Trend measure” ablakban a „no data” feliratú tápanyagokról nincs adat. |
| A „Water by hour” kártya azt írja: „No water in this period has a time.” | Az időszakban csak olyan víz van, amelyet a 34. verzió előtt, időpont nélkül vittél fel. Az új felvitelek időponttal rögzülnek, azok már megjelennek a sávokban. |
| A Report fülön a „Month” a mai hónapnak csak egy részét mutatja | Nem hiba: az időszak a mai napig tart, a fejlécben „so far” áll. A következő napokkal bővül. |
| A Report átlaga kisebb, mint amit egy naplózott napon vártál | Az átlag a naplózott napokra számol, az üres napokat kihagyja. Ha egy sor előtt `≥` áll, valamelyik tételnél hiányzik az adat, a valódi átlag nagyobb is lehet. Nyisd meg a sort: az „Added up from” megmutatja, mely ételekből jön. |
| „N entries in this period are not counted” a Report fülön | Ezeknek a tételeknek az ételadata nem töltődött be (például az USDA- vagy a dmBio-tábla). Kapcsold be az internetet, majd Data fül → „Reload app files”. |
| A „3 months”, „6 months” vagy „Year” gomb szürke a megosztott linken | A link legfeljebb 62 napot tartalmaz, és ezekhez hosszabb időszak kell. Használd a „Week”, a „Month” vagy a „Custom” gombot. |
| Eltűnt az adatom | Töltsd vissza a legutóbbi mentést: Data fül, „Restore from file”. Az app megerősítést kér, mielőtt felülírja az adataidat. |

## Amit érdemes tudnod

- Az általános élelmiszerek adatai a francia CIQUAL 2020 táblából jönnek (3186 étel, 64 tápanyag, francia piaci átlagok, angol nevekkel). A magyar termékeknél a legközelebbi megfelelőt kapod, a pontos érték a címkén van.
- Az USDA adatai az amerikai mezőgazdasági minisztérium FoodData Central adatbázisából jönnek: a Foundation Foods (2026. április, 436 étel) és az SR Legacy (2018, 7793 étel) táblából. Ezek amerikai piaci átlagok, szabadon felhasználható közkincsek. Amit az USDA nem mér, azt az app „nincs adat”-nak hagyja, nem nullának. Három dolgot számolunk: a sót a nátriumból (nátrium × 2,5), a nyers fehérjét a nitrogénből (× 6,25, csak a Foundation ételeknél), és a D-vitamint a nemzetközi egységből (IU × 0,025), ha csak az van megadva. A K2-vitamin az USDA-nál csak az MK-4 forma. A zsírsavaknál csak a pontosan azonosított értéket vettük át, ezért ott több a hiányzó adat. A Foundation táblában néhány étel azonos néven többször szerepel (több minta), ilyenkor az FDC szám különbözteti meg őket.
- Az app 65 tápanyagot ismer: a CIQUAL 64 tápanyagát és a **koffeint** (a 35-ös verziótól). A koffein a CIQUAL táblában nincs benne, ezért az értéke az USDA SR Legacy táblából (az ételek kb. kétharmadánál van adat), az Open Food Facts-ból és a saját ételeidből jön. Ahol nincs adat, ott „no data” áll, nem 0.
- A dmBio termékek (527 db, dm-drogerie markt Magyarország) be vannak építve az appba, a dm.hu termékoldalairól. Az energia és a makrók a dm tápértéktáblázatából jönnek (ahol a táblázat ellentmondott magának, a becslési projekt javította). Minden más érték **becslés** a hozzávalók listájából, a CIQUAL 2020 nyers alapanyagaival (dmBio becslés v3, 2026. október 24.). A becslés átlagérték, nem mérés: a „confidence” mutatja, mennyire bízhatsz benne. Ahol a dm.hu-n nincs táblázat, ott címkeérték sincs. A dmBio ételek NOVA-csoportja üres, azt te állítod be.
- A csomagolt termékek az Open Food Facts közösségi adatbázisból jönnek. A címkeadat hiányos vagy hibás lehet, ezért érdemes összevetni a csomagolással.
- Italoknál az app grammal számol, és 1 ml-t 1 g-nak vesz. Hígabb italoknál ez elég pontos. Ha egy saját ételnél a „100 ml (counted as 100 g)” van kiválasztva (a „Create food” és az „Edit food” ablakban, vagy az AI-válasz 100 ml-es adagja alapján magától), az app **ml-ben mutatja** a mennyiséget, a számolás ettől nem változik. A régebben felvett italok grammban maradnak, amíg az „Edit food” ablakban át nem állítod őket. A CSV `unit` oszlopában ilyenkor `ml` áll.
- Az ajánlott bevitel (Nutrients fül, 16. fejezet) az EFSA felnőttekre vonatkozó értékeiből jön (PRI, AI, nátriumnál és kloridnál SAI). Egyetlen forrást használ, nem keveri a magyar vagy az amerikai (DRI) ajánlásokkal, mert azok átváltása és kora más, és egy rossz átváltás észrevétlenül hibás százalékot adna. A nátrium és a CIQUAL E-vitamin adatáról lásd a 16. fejezet végét.
- Ez egy tájékoztató eszköz, nem orvosi tanács.

**Források:** Anses. 2020. Ciqual French food composition table, <https://doi.org/10.5281/zenodo.4770202> (CC BY 4.0). U.S. Department of Agriculture, Agricultural Research Service. FoodData Central, <https://fdc.nal.usda.gov> (U.S. public domain). dmBio termékek: dm-drogerie markt Magyarország termékoldalai, <https://www.dm.hu>; mikrotápanyag-becslés: dmBio becslés v3 (CIQUAL 2020 alapján). Ajánlott bevitel: EFSA, Dietary Reference Values for nutrients – Summary report (EFSA Supporting Publication 2017:e15121), <https://www.efsa.europa.eu/sites/default/files/2017_09_DRVs_summary_report.pdf>, és a Summary of Dietary Reference Values (4. verzió, 2017. szeptember); nátrium és klorid: EFSA, 2019. Open Food Facts, <https://world.openfoodfacts.org> (ODbL). Vonalkód-olvasó: ZXing-js (Apache 2.0, lásd `ZXING-LICENSE.txt`).
