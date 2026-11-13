# iAlarm MK2 per Home Assistant

[English](README.md) | [Italiano](README.it.md)

[![HACS][hacs-custom-shield]][hacs]
[![Stable Release][stable-shield]][stable]
[![Latest Pre-Release][prerelease-shield]][prerelease]
[![Downloads][downloads-shield]][downloads]
[![Stars][stars-shield]][stars]
[![Forks][forks-shield]][forks]
[![Issues][issues-shield]][issues]
[![Last Commit][lastcommit-shield]][lastcommit]
[![License][license-shield]][license]
[![Maintenance][maintenance-shield]][maintenance]


Integrazione personalizzata di Home Assistant per centrali Meian / iAlarm MK, basata su una copia interna modificata di `pyialarmmk`.

La versione documentata è **[2.3.0-alpha.8](https://github.com/mistermax80/ialarm_mk2/releases/tag/2.3.0-alpha.8)**, pubblicata come pre-release. I metadati HACS indicano **Home Assistant 2026.9.0** come versione minima.

## Funzionalità

| Area | Funzionalità disponibili |
| --- | --- |
| Centrale | Inserimento totale, in casa, parziale e disinserimento; visualizzazione degli stati di allarme e transizione. |
| Zone | Sensori binari con attributi per batteria scarica, perdita collegamento, esclusione e ultima lettura. |
| Esclusione zone | Uno switch di configurazione per ogni zona rilevata; la modifica richiede un aggiornamento riuscito del coordinator e l’allarme disinserito. Lo stato richiesto viene riletto e verificato. |
| Batterie | Percentuale stimata a partire dalla data dell’ultima sostituzione, configurabile per sensore. |
| Diagnostica | Valori di sola lettura per rete, APN mobile e configurazione di sistema. |
| Push | Eventi `ialarm_mk2_event` e sensore binario di connettività push. |
| Manutenzione | Pulsante di riavvio opzionale, disabilitato per impostazione predefinita; richiede l’allarme disinserito. |

### Stima delle batterie

La percentuale viene stimata linearmente su due anni dalla sostituzione: non è una misura della carica reale. Senza una data salvata il valore è sconosciuto, salvo segnalazione di batteria scarica dalla centrale, che imposta il valore al 5%. Disabilitare la stima non nasconde la segnalazione di batteria scarica.

### Diagnostica

Le entità diagnostiche mostrano IP configurato, gateway, DNS, DHCP, APN mobile, ritardi di ingresso/uscita, durata della sirena, impostazioni di perdita collegamento e flag di sistema. Sono **valori di configurazione**, non indicatori di guasto in tempo reale della rete elettrica, wireless o di comunicazione.

Vengono letti una volta all’avvio dell’integrazione e rimangono in memoria fino al suo ricaricamento. Queste entità non permettono di modificare le impostazioni.

### Aggiornamenti ed eventi

Gli stati delle zone vengono letti con l’intervallo configurato, pari a 60 secondi per impostazione predefinita. Lo stato dell’allarme viene letto inizialmente e poi mantenuto tramite eventi push e aggiornamenti locali dei comandi; il polling delle zone non rilegge `GetAlarmStatus`.

Il sensore di connettività indica se è stato ricevuto un messaggio push di associazione/keepalive negli ultimi due minuti circa. Non verifica separatamente la connessione dei comandi.

Per usare gli eventi push nelle automazioni, ascolta `ialarm_mk2_event` in Home Assistant. I dati comprendono `Cid`, `Status`, `Zone`, `ZoneName`, `Content` e `LastRealUpdateStatus`; le informazioni disponibili dipendono dall’evento ricevuto.

## Installazione

### HACS

Aggiungi questo repository a HACS come repository personalizzato di tipo **Integrazione**:

```text
https://github.com/mistermax80/ialarm_mk2
```

Installa l’integrazione e riavvia Home Assistant. Per installare `2.3.0-alpha.8`, abilita le versioni pre-release nella scelta della versione da scaricare in HACS.

### Installazione manuale

1. Scarica la versione desiderata dalle [release GitHub](https://github.com/mistermax80/ialarm_mk2/releases).
2. Copia la cartella `custom_components/ialarm_mk2` della release in `<config>/custom_components/ialarm_mk2`, mantenendone il contenuto.
3. Riavvia Home Assistant.

## Configurazione

Apri **Impostazioni → Dispositivi e servizi → Aggiungi integrazione** e cerca **iAlarm-MK Integration 2**. Inserisci host (indirizzo IP o nome host), porta, ID centrale/nome utente, password e intervallo di lettura delle zone. L’host predefinito è l’indirizzo del server impostato nell’integrazione.

Usa **Riconfigura** per cambiare connessione o intervallo di lettura. Nelle opzioni dell’integrazione, espandi la sezione del sensore per indicare la data dell’ultima sostituzione della batteria. Disattiva `disable_battery_estimate` per abilitare la stima; lasciarlo attivo cancella la data salvata. Le date future non sono accettate.

I nomi delle entità sono disponibili in italiano e inglese. I nomi personalizzati dall’utente vengono mantenuti. Le sezioni delle opzioni batteria usano attualmente i nomi dinamici dei sensori e gli identificativi dei campi (`battery_replacement_date`, `disable_battery_estimate`).

## Limiti attuali e sviluppi previsti

- `GetLog` e `GetEvents` esistono nella libreria interna, ma non sono esposti come funzioni di recupero dello storico in Home Assistant. Gli eventi push sono già supportati.
- Le impostazioni di sistema sono di sola lettura; `SetSys` non è esposto.
- La configurazione delle zone e un’azione separata per annullare l’allarme attivo non sono esposte.
- L’attivazione SOS/emergenza non è esposta.

## Log e test offline

L’integrazione non registra più l’intera config entry nei log diagnostici e non include token di autenticazione nei messaggi di login, logout e chiusura socket. Nei relativi errori rimangono operazione e tipo di eccezione, senza testo grezzo dell’eccezione. Questo non elimina i log già esistenti e non costituisce una redazione universale dei log prodotti da altro codice.

Sono presenti nove test automatici per errori/backoff push e protezione dei log sensibili. Dalla radice del repository, in un ambiente Python con Home Assistant, `lxml` e `xmltodict`, esegui:

```sh
python -B -m unittest discover -s custom_components/ialarm_mk2/tests -v
```

I test simulano le comunicazioni e non si collegano a una centrale reale.

## Ringraziamenti

- [meian-client](https://github.com/wildstray/meian-client)
- [pyialarm](https://github.com/RyuzakiKK/pyialarm)
- [pymeianlike](https://github.com/bigmoby/pymeianlike)
- [ialarm-mqtt](https://github.com/maxill1/ialarm-mqtt)

[hacs-custom-shield]: https://img.shields.io/badge/HACS-Custom%20Repository-blue?style=for-the-badge
[hacs]: https://hacs.xyz/repository/github/mistermax80/ialarm_mk2

[stable-shield]: https://img.shields.io/github/v/release/mistermax80/ialarm_mk2?label=Stable&sort=semver&style=for-the-badge
[stable]: https://github.com/mistermax80/ialarm_mk2/releases/latest

[prerelease-shield]: https://img.shields.io/github/v/release/mistermax80/ialarm_mk2?include_prereleases&label=Pre-Release&sort=semver&style=for-the-badge
[prerelease]: https://github.com/mistermax80/ialarm_mk2/releases

[downloads-shield]: https://img.shields.io/github/downloads/mistermax80/ialarm_mk2/total?style=for-the-badge
[downloads]: https://github.com/mistermax80/ialarm_mk2/releases

[stars-shield]: https://img.shields.io/github/stars/mistermax80/ialarm_mk2?style=for-the-badge
[stars]: https://github.com/mistermax80/ialarm_mk2/stargazers

[forks-shield]: https://img.shields.io/github/forks/mistermax80/ialarm_mk2?style=for-the-badge
[forks]: https://github.com/mistermax80/ialarm_mk2/network/members

[issues-shield]: https://img.shields.io/github/issues/mistermax80/ialarm_mk2?style=for-the-badge
[issues]: https://github.com/mistermax80/ialarm_mk2/issues

[lastcommit-shield]: https://img.shields.io/github/last-commit/mistermax80/ialarm_mk2?style=for-the-badge
[lastcommit]: https://github.com/mistermax80/ialarm_mk2/commits/main

[license-shield]: https://img.shields.io/github/license/mistermax80/ialarm_mk2?style=for-the-badge
[license]: https://github.com/mistermax80/ialarm_mk2/blob/main/LICENSE

[maintenance-shield]: https://img.shields.io/maintenance/yes/2026?style=for-the-badge
[maintenance]: https://github.com/mistermax80/ialarm_mk2
