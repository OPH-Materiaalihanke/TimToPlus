A+ tiedostot täytyy ladata erikseen. Joko hae virallisislta sivuilta course-template ja kopioi sen sisältö 'CourseData' kansioon, tai lataa pelkistetty versio kurssitiedostoista komennoilla
~~~
git submodule init
git submodule update
~~~

Käyttö:
=====

Aluksi
------

*courseinfo-.py* sisältää kurssikohtaiset asetukset, jotka tulee asettaa jokaiselle 
kurssille erikseen. Aloita kopioimalla tämä tiedosto, ja nimeä kopio samaksi, ilman 
viimeiät väliviivaa. Näin asetukset eivät palaudu, vaikka projekti ladattaisiin 
uudestaan.

Nyt voit kirjoittaa asetukset valmiiksi. Tärkein osuus infoa on kurssiin kuuluvien
sivujen nimeäminen. Skripti käyttää tätä listaa lataamaan tiedostot tarvittaessa, 
ja luo kansiorakenteet sen mukaan.

Sitten
------

*courseinit.py* alkaa muutamalla lisäasetuksella, jotka täytyy tarkistaa ennen 
skriptin ajamista, tärkeimpänä evästeen päivittäminen, jotta uudet tiedostot 
saadaan tarvittaessa ladattua TIMin servereiltö.

Jonka jälkeen
-------------

Kun *courseinit.py* on ajettu onnistuneesti, kurssia voidaan kokeilla kuten normaalisti: 
Olettaen että A-Plus -kurssien käyttöönotto ohjeita on noudatettu, Docker on asennettu, ja 
kurssi voidaan kääntää komennolla
~~~
sudo ./docker-compile.sh
~~~
