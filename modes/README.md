# ME2 Modes

The gameplay of ME2P is divided into a few broad categories, outlined below.

If you're reading this, you're probably interested in examples of MPF game design
and looking for reference material. To help navigate the dozens of modes in ME2,
each mode below lists a few behaviors it implements.

Most modes use a hurryup and multiplier for scoring, with consecutive shots
increasing the multiplier (e.g. restarting missions offers a lower possible
multiplier) and shots banking the hurryup values. Details of each modes's scoring
are noted in the mode config files, above the `variable_player` section.

### Recruitment Missions
Recruitment missions compromise the bulk of the gameplay and are unlocked by
hitting their corresponding shots 3x. There are 10 recruitment missions,
corresponding to the 10 recruitable squadmates. Each mode uses a hurryup value
on its shots and a timer that will end the mode.

Some modes preserve their state if they have to be restarted, while others reset
on each start. One mode (Thane) resets itself but lowers the requirement count
for completion on subsequent starts.

*Individual Recruitment Missions:*

* **[Garrus](recruitgarrus/config/recruitgarrus.yaml)** - Defend Archangel
  * Complete a set of lit shots to light a final shot
  * Hit the final shot to complete the mode
  * Reset the set of shots when the mode restarts
* **[Grunt](recruitgrunt/config/recruitgrunt.yaml)** - Defeat the Tank-Bred
  * Light a set of shots
  * Count the number of lit shots that are hit
  * Reset the timer when a lit shot is hit
  * Complete the mode when the counter hits a specified value
  * Save the state of shots/counter when the mode restarts
  * Play a sound, specified depending on the count of shots hit
* **[Jack](recruitjack/config/recruitjack.yaml)** - Escape from Purgatory
  * Light a set of shots, hit any to light a bank, hit bank to complete a round
  * Light a different set of shots for the next round, hit any to light the bank
  * Complete the mode when a number of rounds are completed
  * Save the count of completed rounds but restart the round when the mode restarts
* **[Kasumi](recruitkasumi/config/recruitkasumi.yaml)** - Infiltrate the Vault
  * Light one shot as a "don't hit" shot
  * When an un-lit shot is hit, light it as "don't hit"
  * Count the number of un-lit shots that are hit
  * Complete the mode when the counter reaches a specified value
  * Count the number of lit shots that are hit
  * Fail the mode when a certain number of lit shots are hit
  * Play a specified sound/slide on each shot hit, depending on the counters
* **[Legion](recruitlegion/config/recruitlegion.yaml)** - Stop the Heretics
* **[Mordin](recruitmordin/config/recruitmordin.yaml)** - Cure the Plague
  * Light the spinner to hit first, then light the right orbit to hit second
  * Once both are hit, light both ramps
  * Hit both ramps (in either order) to complete the mode
  * Play a semi-random sound on each hit (dependent on which squadmates are recruited)
* **[Samara](recruitsamara/config/recruitsamara.yaml)** - Chase Morinth
  * Light all standup targets
  * Hit a standup target to light the lanes on either side
  * Hit a certain number of lit lanes to complete the mode
  * Preserve the state of targets/lane shots when restarting
* **[Tali](recruittali/config/recruittali.yaml)** - Destroy the Colossus
  * Light a specific shot with a multiple-step shot profile
  * Hit the shot to advance the profile
  * Complete the mode by hitting the shot to the final profile state
  * Fail the mode when the timer runs out
  * If the mode fails, step the shot profile back one state
* **[Thane](recruitthane/config/recruitthane.yaml)** - Ascend Dantius Tower
  * Light two ramps and count their hits
  * When the ramps counter reaches a certain value (3 shots on the first play, 1 shot on repeat plays), light the orbit shots
  * Continue hitting ramps to build value
  * Hit either orbit to complete the mode and collect the value
* **[Zaeed](recruitzaeed/config/recruitzaeed.yaml)** - Assault the Refinery
  * Light two shots, one red and one blue, to indicate two "paths" for the player
  * After a path is chosen, light a set of shots and count their hits
  * When a lit shot is hit, add some time to the timer and play a sound based on the chosen path
  * Complete the mode when the counter reaches a specified value
  * Clear the chosen path and reset the counter when the mode restarts

### Story Missions
Story missions are the mini and full-sized wizard modes of the game and are
unlocked by completing recruitment missions. There are 4 story missions, some of
which are selectable from the Mission Select and some of which are triggered
automatically.

####Collector Ship
The Collector Ship mission becomes available after four squadmates have been recruited, and
is started from the mission select screen. No other recruitment missions can be played and
the Collector Ship can not be bypassed.

It consists of a "base" mode that runs underneath and manages the three "phase" modes,
which cycle through as long as the player is able to maintain them. The mode (and
corresponding achievement) are considered "complete" after the third phase is beat. Prior
to completion the mode will play until the ball ends, but if the player beats the third
phase then the mode will stop when only one ball remains.

* **[Base mode](collectorship_base/config/collectorship_base.yaml))**
  * Start the mini-wizard mode and manage the transition between phases
  * Handle common sound files shared between phases
  * Start a multiball and add balls on certain events
* **[Ambush Phase](collectorship_ambush/config/collectorship_ambush.yaml)**
  * Light all shots and count each one being hit
  * Add a ball (up to a maximum number) when a lit shot is hit
  * Play a sound when only one shot remains
  * Complete the phase when all shots are hit
* **[Husk Phase](collectorship_husk/config/collectorship_husk.yaml)**
  * Start a timer and light all standup targets
  * Hit a lit standup to light a random lane shot and add value
  * Hit a light lane to collect/reset the added values
  * Store the total sum of all values added/collected
  * Play sounds depending on which squadmates have been recruited
  * End the phase automatically when the timer runs out
* **[Praetorian Phase](collectorship_praetorian/config/collectorship_praetorian.yaml)**
  * Start a timer for the Praetorian's "attack"
  * Light one random lane and one random bank
  * Hit either lit shot to increment a counter and light new random shots
  * If the "attack" timer runs out, play a show and disable one flipper
  * Re-enable the flipper by hitting a lit shot
  * Complete the shots counter to complete the mode and return to the Ambush phase
  * If the "attack" timer runs out a second time, regress back to the Husk phase

This mode can only be played once.

####Derelict Reaper**
This mode can be selected from the Misson Select when the player reaches level 8
(by recruiting squadmates and/or completing other missions), but it does not have
to be played immediately. The player can choose to continue recruiting and doing
side missions until they choose to play the Derelict Reaper.
  * Two-ball multiball when the mode starts
  * Light all lane shots on a timer (with a hurryup)
  * When the timer runs out, the lane shots are disabled and the hitbank is lit
  * Hitting the hitbank re-lights the lane shots, re-starts the timer, and adds a ball (if only one is in play)
  * Hitting all the lanes lights the jackpot shot
  * Hitting the jackpot shot awards the combined hurryup and completes the achievement
  * Prior to jackpot completion, the mode only ends if the ball ends
  * After jackpot completion, the mode ends when the player drains to one ball

This mode can only be played once.

#### Normandy Attack
This mode is driven from a pop bumper counter that starts after the Derelict Reaper is played.
When the counter reaches zero, all other modes stop and the Normandy Attack begins immediately.
  * Override all light, sound, and slide plays to simulate machine shutdown
  * Shut off flippers and force a ball drain while a show plays
  * Enable a secret ball save to resume play without costing a player ball
  * Stagger the drain, ball save, trough eject, and auto-plunge events based on sound playback
  * Light a pre-set sequence of shots to hit for completion
  * Use sequence shots to detect ramp shot failures
  * Light an outlane ball save on each shot completion

#### Suicide Mission
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

#### Lair of the Shadow Broker
This is a series of unlockable modes governed by the [global shadowbroker mode](global/config/global_shadowbroker.yaml). The global mode handles the tracking/lighting of dropbank hits to enable the series of mini-wizard modes:
* **[Vasir Chase](shadowbroker_chase/config/shadowbroker_chase.yaml)** is a typical timed follow-the-shots-sequence with a pre-determined set of shots.
  * Light a shot and advance through a specific order of shots using *hit_events* and *enable_events*
  * Play a progression of success sounds as the lit shots are hit
  * Play a randomization of wrong-way sounds when the wrong shots are hit
  * Don't end the ball on drain, instead end the mode and return to the normal playfield
  * If the player fails, restart them one shot back from where they left off
* **[Vasir Combat](shadowbroker_vasir/config/shadowbroker_vasir.yaml)** is a follow-the-shot mode where the player must hit a shot that "jumps" around the playfield
  * Define a sequence of shots in a shot_group with a rotation order
  * Light a "target" shot with a profile state and start a timer
  * If the timer runs out, rotate the target to a different shot
  * If the target is hit: reset the timer, advance the profile state, rotate the target to a different shot *(this logic is way more complex than you'd think)*
  * Complete the mode by hitting the target on its final profile state
* **[Hagalaz Ship](shadowbroker_hagalaz/config/shadowbroker_hagalaz.yaml)** 
  * Define a group of shots and randomly light one every 8 seconds
  * Hit a lit shot to advance a counter
  * Use lights to indicate standup targets "charging up" over 10s
  * Hit a "charged" standup to register a hit on the shots to either side of it
  * Stop all timers and charging when the counter hits its target value
  * Light a special ball hold shot to finish the mode
* **[Boss Combat](shadowbroker_boss/config/shadowbroker_boss.yaml)**

#### Multiballs
There are two multiball modes, both of which are lit and locked in the same way via the [global multiball handler](global/config/global_multiball.yaml). Prior to the Collector Ship mission
it's Overlord that can be played; after it's Arrival.
* **[Overlord Multiball](overlord/config/overlord.yaml)** is a typical multiball that will run as long as there are multiple balls in play.
  * Light all lanes with a hurryup to build value
  * Hit one lane to enable a "jackpot" shot and add time to the timer
  * Continue hitting lit lanes to build more value; hit the jackpot to collect
  * After each jackpot collection, it takes one more lane shot to re-light (up to every lane)
  * Collect 3 jackpots to complete the mode and the achievement
  * If the timer runs out, all lane shots "freeze" and must be reset
  * The mode ends when the balls drain down to one
* **[Arrival Multiball](arrival/config/arrival.yaml)** is a timed multiball that runs in phases synchronized with music.
  * Start a music track and synchronize the start/stop of phases to markers in the music
  * Maintain multiple multiballs with decreasing ball counts
  * Phase 1 (save 3 balls): light all lanes with compound scoring to build value
  * Phase 2 (save 2 balls): light all targets for points to add value
  * Phase 3 (save 1 ball): light all lanes for increasing the multiplier
  * Phase 4 (no ball save): light the escape shot and start the hurryup
  * If the escape shot is hit, award the complete built value X the multipliers
  * If the escape shot is not hit, award a portion of the built value
  * If the ball drains, award a smaller portion of the built value

* **[N7 Assignments](n7_assignments/config/n7_assignments.yaml)** are single-shot modes that
are started automatically each time the pop bumper count is completed.
  * Light a random "mission" shot through random_event_player
  * Display a dynamic value on a slide using event_player arguments
  * Set a hurryup value on a timer and show it ticking down
  * Award the hurryup value if the shot is hit
  * End the mode if the timer runs out

### Supplemental Modes
These modes can be triggered throughout the game and offer bonuses, multipliers, extra points, and
other goodies. They have to be enabled/unlocked and activated, but do not supercede any existing
gameplay modes.
* **[Harbinger](harbinger/config/harbinger.yaml)** provides a stackable playfield multiplier
* **[Research Upgrades](upgrades/config/upgrades.yaml)** provide additional shot bonuses after missions are completed
* **[Shopping](shopping/config/shopping.yaml)** provides purchasable items to help win missions

### Game Logic Modes
Game logic modes handle underlying behavior and are not exposed to the player but do interesting things behind-the-scenes.

#### Base
* **[Base](base/config/base.yaml)** handles the fundamental gameplay and exists beneath all other modes. It handles the transitions between *global* and various wizard modes.
* [Medigel](base/config/base_medigel.yaml) handles a special outlane ball save that can
be enabled by events throughout the game and will save one outlane drain (if no other
ball saves are active).

#### Global
* **[Global](global/config/global.yaml)** handles the transitions between *field* and various mission modes, as well as common gameplay behaviors that exists in non-wizard play.
* [Multiball](global/config/global_multiball.yaml) handles the lighting and lock-enabling of multiballs, since both Overlord and Arrival multiball modes use the
same lighting/locking behavior.
  * Use achievement states to determine which multiball mode is being advanced
  * Enable a "light lock" shot on two hitbanks
  * Hit either hitbank to disable the "light" shot and light the "lock" shot
  * Hit the lock shot to lock a ball, play a sound and slide, and re-enable the light shot
  * Lock three balls to start the appropriate multiball mode
  * After a multiball has been played, it can be lit/locked again but *both* hitbanks must be hit to light the lock.
* [Planets](global/config/global_planets.yaml) handles the pop bumper and top lane
behaviors, including multipliers and countdown awards.
* [Recruit](global/config/global_recruit.yaml) handles the lighting and tracking of
recruitment shots, allowing players to advance towards recruitment missions and playing
sounds/slides when those missions are completed. It also handles a common ball save
that runs when any recruit mission starts.
* [Shadow Broker](global/config/global_shadowbroker.yaml) handles the dropbank hits
that progress towards the various Shadow Broker modes.
  * Track dropbank completions and play a specific sound on each drop
  * Light up to three lights to indicate the completion progress
  * Complete one set of three to enable the chase
  * While the chase is enabled, complete the dropbank to start the chase mode
  * After the chase is completed, hit the ball hold to start the vasir mode
  * After vasir is completed, track and light up another three dropbank completions
  * On the third completion, enable the hagalaz mode
  * While hagalaz is enabled, complete the drapbank to start the mode
  * After hagalaz is completed, hit the ball hold to start the broker mode
  * After the broker is completed, additional dropbanks award bonus points

#### Field
* **[Field](field/config/field.yaml)** handles all playfield behavior when no mission or wizard mode is active. 

#### Other
* **[Bonus](bonus/config/bonus.yaml)** awards extra points after a ball has ended
* **LockHandler** handles the logic for the physical ball lock between multiball locks, mission select holds, and lock bypass. Includes both a [mode config.yaml](lockhandler/config/lockhandler.yaml) and a [custom python mode](lockhandler/code/lockhandler.py) for the advanced logic
  * Watch the ramp entrance for an incoming ball towards the ball lock
  * Use a *queue_relay_player* to delay a ball eject event
  * Add event handlers and post events through mode's custom code
  * Determine if the ball should be held or locked based on complex criteria
    * Is lock lit?
    * Will the multiball be filled?
    * Are any missions available?
    * Will the completion of the ramp shot enable any missions?
    * Does a specialist need to be selected?
    * Is a wizard mode active?
    * Is the field mode active?
* **Mission Select** enables the player to choose an available mission mode to start. Includes both a [mode config.yaml](missionselect/config/missionselect.yaml) and a [custom python mode](missionselect/code/missionselect.py) to determine which missions are available. This mode also handles the selection of specialists during the Suicide Mission.
  * Extend the *Carousel* mode in a custom mode code
  * Dynamically build a list of carousel items based on variables and mode states
  * Broadcast events with arguments based on selection type


