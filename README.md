# Mass Effect 2: the Pinball Game

*"I'm Commander Shepard, and this is my favorite pinball game on the Citadel."*

Recruit a squad from the most skilled soldiers, biotics, and technicians across dozens of worlds. Survive the journey through the Omega 4 Relay and lead a suicide mission to the enemy's front door. Sacrifice everything, stand your ground, and save the galaxy.

**[Mass Effect 2: the Pinball Game](https://masseffectpinball.com)** brings the challenge and excitement of BioWare's sci-fi epic to the arcade table so you can re-live the most exciting missions of Commander Shepard's quest as a brand-new pinball experience. From the slums of Omega to the towers of Illium and from the decks of the Normandy to the heart of the Collector base, the Mass Effect 2 Pinball Game is the ultimate challenge for Spectres of the steel ball.

See the completed machine at https://masseffectpinball.com.

## Requirements

This project requires the Mission Pinball Framework 0.52+ and can be simulated using the MPF virtual machine and MPF monitor interface. Playing in the real world requires either a FAST-based pinball machine or a Stern Game of Thrones Pro Edition pinball machine and the MPF-Spike-Bridge, or you are welcome to build a config file for your particular hardware setup.

### Installation
Clone the repo into the folder of your choosing, and install the [Mission Pinball Framework](http://docs.missionpinball.org/en/latest/install/index.html) (MPF).

#### Release Versions
Mass Effect 2 Pinball maintains "release" versions compatible with the major and minor releases of MPF. The release versions may have
placeholders where sigificant changes are being developed, but are fully playable. The newest release will always be the default, but
you may download any release branch that corresponds to your version of MPF.

#### Developer Version
Both MPF and Mass Effect 2 Pinball are under constant development, with new features and improvements added every few days. The developer version of Mass Effect
is considered stable but requires the latest dev release of MPF. You can upgrade your MPF to pre-release versions like so:
```
pip install mpf mpf-mc --pre --upgrade
```

More details on installing MPF are available [in the MPF Documentation](http://docs.missionpinball.org/en/latest/install/index.html).

### Running with Config Options

* **-x for virtual** The default configuration for ME2 Pinball is a homebrew FAST machine, which can be virtualized with the `-x` parameter.
* **--no-sound** The audio files for ME2 Pinball are extracted from Mass Effect 2 directly and are not included in the repo. To avoid missing file errors, audio can be disabled with the `--no-sound` parameter.

Therefore, the simplest way to see ME2 in action is to run the following command from the repo folder:

```
$ mpf both -x --no-sound
```

### Running on Stern Game of Thrones

ME2 Pinball was alpha-tested (and can still be played) on a Stern Game of Thrones Pro machine with the [MPF Spike Bridge](http://docs.missionpinball.org/en/latest/hardware/spike/mpf-spike-bridge.html) installed. This fully-playable version features the complete gameplay along with lighting effects and use of the built-in DMD screen.

To play Mass Effect 2 on Game of Thrones, you must first change your local *hardware_spike.yaml* file and set the spike `port:` that corresponds to your local machine's serial connection to the Spike machine (as detailed in the instructions linked above). Then you can run MPF with the "spike" configuration file.

```
$ mpf both --no-sound -c spike
```

Different hardware setups and USB-Serial cables have varying throughput for communication with the Stern Spike boards. In the file *hardware_spike.yaml* you can adjust the `runtime_baud:` setting to any number from the [MPF Spike Bridge baudrates](https://github.com/missionpinball/mpf-spike/blob/master/src/main.rs#L435). A higher number will increase responsiveness but may decrease stability. If your Game of Thrones machine loses sync or coils stop working, try reducing the number.

###

## Main Gameplay

**Spoiler Warning:**
*In recreating the full experience of Mass Effect 2, the Pinball Game includes significant characters and story events from the original game.*

### Recruitment Missions
The core challenge of the ME2 Pinball Game is to recruit a squad to take with you on the Suicide Mission. When the game starts all five of the major shots are lit with a squadmate to recruit—hit a shot three times to light that squadmate's recruitment mission. After a squadmate is recruited, a second squadmate's recruitment light will appear on that same shot (for a total of ten possible recruitment missions). Once lit, a recruitment mission can be started from the left ramp.

* **The Professor - Curing the Plague**

  Hit the spinner to build value and the right orbit to place the cure and add multipliers. Hit both fan shots to disburse the cure and complete the mission.

* **Archangel - Siege on Omega**

  Take out mercenaries for points and hit each of the three lit shots to close the shutters and stop the assault. Get upstairs and protect Archangel to complete the mission.

* **The Warlord - Defeating the Tank-Bred**

  Hit each lit shot to defeat a tank-bred Krogan. Finish all shots to complete the mission.

* **The Convict - Escaping Purgatory Prison**

  Hit any lit shot to build points and unlock a prison door, then hit the right hitbank to collect the value and advance through the prison. Advance three times to complete the mission.

* **The Thief - Breaking and Entering**

  Hit any un-lit shot to infiltrate the stronghold, but watch out! After every round another shot will be alarmed, and hitting any alarm shot fails the mission! Advance four times to complete the mission.

* **The Assassin - Assaulting Dantius Towers**

  Advance up the ramps to build value and ascend the towers. Once high enough, hit one of the orbits to cross the bridge and complete the mission.

* **The Quarian - Geth on Haestrom**

  Hit the lit shot to weaken the Geth Colossus. Hit the Colossus six times to defeat it and complete the mission, but hurry! The Colossus will self-repair after a few seconds, requiring an additional hit to defeat.

* **Legion - Hacking the Heretics**

  Hit the lit shots to defend the console, then hit the kickback lane to complete the hack. If you're not fast enough, geth shots will light on the banks and must be hit before progress can continue.

* **The Mercenary - Blue Suns Refinery**

  Choose the blue shot to rescue the factory workers (with higher hurry-up times), or the red shot to pursue Vido (with higher multipliers), and hit either orbit to advance the mission. Hit the kickback to collect your jackpot and complete.

* **The Justicar - Chasing Morinth**

  Hit the standup targets to damage the gunship's armor, hit the lit shots to collect value. Hit five shots to complete the mission.

### Collector Missions
At various points in the game, special missions will become available which present Commander Shepard with opportunities to face the Collectors head-on. Some of these missions are unlocked based on the number of squadmates recruited, others are unlocked based on the player's level.

* The Collector Ship

  Survive waves of ambushing Collectors and hordes of Husks before facing off with the Praetorian in this high-intensity multiball.

* The Derelict Reaper

  Speed is the name of the game in this high-stakes multiball as Commander Shepard must fight through waves of husks and scions to find the IFF and get out before the Reaper falls.

* The Collector Attack

  Follow the Normandy's emergency lighting and avoid Collector forces as you make your way towards an escape in this dark survival mission.

### The Suicide Mission
Advance far enough in ME2 Pinball to unlock the Suicide Mission, a multi-part wizard mode that pits you and your squad against the toughest challenges ever faced.

* Passing the Omega 4 Relay

  Bring your ship upgrades and make your stand against oculus sentries and the behemoth Collector ship in this chaotic timed multiball.

* Infiltrating the Collector Base

  Choose a tech specialist to enter the vent, then follow the lit shots to open the valves and get them through safely—fighting Collectors all the while in this exciting two-ball battle. Don't let the timer run out!

* The Long Walk

  Choose a biotic specialist to protect the squad and follow the blue shots to make your way deeper into the base, battling husks and Collectors along the way. Move quickly, don't stray from the biotic barrier, and don't let your squadmates get too far behind if you want to survive!

* The Reaper

  Knock out the supporting tubes and set a bomb to destroy the base, then finish the fight in a two-phase battle that alternates between taking down Collectors during a four-ball multiball and playing cat-and-mouse against a Reaper. Build up attack damage and hit the Reaper repeatedly to take it down, but watch out for its deadly beam cannon!

* Escape

  Get your surviving squadmates to safety and build up value during this high-speed multiball, then hit the final shot to destroy the base and complete the Suicide Mission.

## Side Missions

### Lair of the Shadow Broker
Drop the bank of targets to gather intel on the Shadow Broker and start this mini-wizard mode. Complete three banks to unlock the Vasir car chase, then follow the shots and defeat Vasir in combat to get the data disk. Complete additional drop banks to unlock Hagalaz, then storm the Shadow Broker's ship and defeat his mercenaries to meet him face-to-face in a high-stakes two-ball battle.

### Overlord
Hit the Geth target banks to clear a station on Aite and hit the left ramp to lock a ball and disable the geth. When all three stations are complete the Overlord three-ball multiball begins: hit the glowing shots to build value, and watch out for the blinking lights of data upload shots. When they appear, no more value can be built until the uploads are destroyed.

*This mission is only available prior to the Collector Ship mission*

### Arrival
Hit the Batarian target banks to clear a path through Project Base and hit the left ramp to lock a ball and get the station online. When all three systems are restored the Arrival three-ball multiball begins: hit the lit shots to build value and the pulsing shot for multipliers as the station heads towards Alpha. Watch out for the timer and make sure to hit the escape shot before time runs out!

*This mission is only available after the Collector Ship mission*

### Project Firewalker
Scan research packets to uncover intel at sites scattered across the galaxy. Collect three packets from any site to unlock increasingly difficult recovery missions in the M-44 Hammerhead vehicle. Complete all the missions to unlock the hidden Prothean site: a fast-paced rocket-drone multiball!

## Additional Gameplay

### N7 Assignments
Complete the pop-bumper counter to enable an N7 assignment, a single random shot on a hurryup. Hit the shot to complete the assignment. Complete more assignments to unlock *N7: Hahne Kader Facility*, a whack-a-mole multiball against waves of mechs.

### Planet Scanning
Complete the top lanes to scan a planet, increasing the efficacy of your mineral scanner (earned via pop bumper hits) and raising the minerals bonus awards. Scan additional planets to unlock the *Normandy Crash Site*, a timed free-shoot that unlocks powerful rewards.

### Harbinger
During missions against the Collectors, Harbinger will occasionally appear at the captive ball. While Harbinger is present, two hits will start a timed 2x playfield multiplier and additional hits will increase the multiplier (up to 6x). The multiplier duration persists even after Harbinger leaves, but will end when the mission is completed.

## Credits

Mass Effect 2 is an amazing piece of work by BioWare.

ME2 Pinball is a labor of love by Anthony van Winkle.
