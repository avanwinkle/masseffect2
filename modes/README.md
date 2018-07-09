# ME2 Modes

The gameplay of ME2P is divided into a few broad categories:

### Recruitment Missions
Recruitment missions compromise the bulk of the gameplay and are unlocked by
hitting their corresponding shots 3x. There are 10 recruitment missions,
corresponding to the 10 recruitable squadmates.

*Common Recruitment Modes:*

* **[Recruit Base](recruitbase/config/recruitbase.yaml)** handles the
underlying/common logic for enabling/disabling/awarding recruitment missions
* **[Recruit Field](recruitfield/config/recruitfield.yaml)** handles the basic
gameplay for unlocking recruitment/side missions and is the default mode when
no other gameplay mode is active

*Individual Recruitment Missions:*

* **[Garrus](recruitgarrus/config/recruitgarrus.yaml)** - Defend Archangel
* **[Grunt](recruitgrunt/config/recruitgrunt.yaml)** - Defeat the Tank-Bred
* **[Jack](recruitjack/config/recruitjack.yaml)** - Escape from Purgatory
* **[Kasumi](recruitkasumi/config/recruitkasumi.yaml)** - Infiltrate the Vault
* **Legion** - Stop the Heretics
* **[Mordin](recruitmordin/config/recruitmordin.yaml)** - Cure the Plague
* **Samara** - Chase Morinth
* **[Tali](recruittali/config/recruittali.yaml)** - Destroy the Colossus
* **[Thane](recruitthane/config/recruitthane.yaml)** - Ascend Dantius Tower
* **Zaeed** - Assault the Refinery

### Story Missions
Story missions are the mini and full-sized wizard modes of the game and are
unlocked by completing recruitment missions. There are 4 story missions, some of
which are selectable from the Mission Select and some of which are triggered
automatically.

* **Collector Ship** ([base mode](collectorship_base/config/collectorship_base.yaml))
  * [Ambush Phase](collectorship_ambush/config/collectorship_ambush.yaml)
  * Husk Phase
  * Praetorian Phase
* **Derelict Reaper**
  * Reaper Multiball
  * IFF Lock
* **Collector Attack**
* **Suicide Mission**
  * Omega 4 Relay
  * Infiltration
  * the Long Walk
  * the Human Reaper
    * Collector Phase
    * Reaper Phase
  * the End Run / Escape

### Side Missions
Side missions provide additional gameplay during the course of collecting
recruitment missions, and are unlocked by hitting various targets/banks/bumpers.
* **Lair of the Shadow Broker** ([base mode](shadowbroker/config/shadowbroker.yaml))
is a series of unlockable modes leading to a big boss finish
  * Vasir Chase
  * Vasir Combat
  * Hagalaz Ship
  * Boss Combat
* **[N7 Assignments](n7_assignments/config/n7_assignments.yaml)**
* **Project Overlord** and **Arrival** are multiball modes
  * [Overlord Multiball](overlord/config/overlord.yaml)
  * [Arrival Multiball](arrival/config/arrival.yaml)
  * [Global Multiball Manager](global/config/global_multiball.yaml)

### Supplemental Modes
These modes can be triggered throughout the game and offer bonuses, multipliers, extra points, and
other goodies. They have to be enabled/unlocked and activated, but do not supercede any existing
gameplay modes.
* **[Harbinger](harbinger/config/harbinger.yaml)** provides a stackable playfield multiplier
* **[Research Upgrades](upgrades/config/upgrades.yaml)** provide additional shot bonuses after missions are completed
* **[Shopping](shopping/config/shopping.yaml)** provides purchasable items to help win missions

### Game Logic Modes
Game logic modes handle underlying behavior and are not exposed to the player but do interesting things behind-the-scenes.

* **[Base](base/config/base.yaml)** handles the fundamental gameplay and exists beneath all other modes
* **[Bonus](bonus/config/bonus.yaml)** awards extra points after a ball has ended
* **LockHandler** handles the logic for the physical ball lock between multiball locks, mission select holds, and lock bypass. Includes both a [mode config.yaml](lockhandler/config/lockhandler.yaml) and a [custom python mode](lockhandler/code/lockhandler.py) for the advanced logic
* **Mission Select** enables the player to choose an available mission mode to start. Includes both a [mode config.yaml](missionselect/config/missionselect.yaml) and a [custom python mode](missionselect/code/missionselect.py) to determine which missions are available
* **[Planetary Exploration](planets/config/planets.yaml)** builds value and multipliers via pop bumpers


