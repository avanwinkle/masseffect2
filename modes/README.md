# ME2 Modes

The gameplay of ME2P is divided into a few broad categories, outlined below.

If you're reading this, you're probably interested in examples of MPF game design
and looking for reference material. To help navigate the dozens of modes in ME2,
each mode below lists a few behaviors it implements.

Most modes use a hurryup and multiplier for scoring, with consecutive shots
increasing the multiplier (e.g. restarting missions offers a lower possible
multiplier) and shots banking the hurryup values. Details of each modes's scoring
are noted in the mode config files, above the `variable_player` section.

Mass Effect 2 pinball is the basis for the MPF documentation's [Mode Layering Guide](http://docs.missionpinball.org/en/dev/game_design/mode_layering.html) for how to
structure and transition between playfield, mission, and wizard modes, so reviewing
that guide may be helpful in understanding how the below modes behave.

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
  * Hit any lit shot to start a countdown timer
  * Hit a second shot before the timer runs out to advance and reset the timer
  * Hit a third shot to complete the mode and light a bonus shot
  * Hit the bonus shot to collect extra points
  * If the between-shot timer expires, progress is paused and a bank shot must
    be hit to re-enable the main shots
* **[Mordin](recruitmordin/config/recruitmordin.yaml)** - Cure the Plague
  * Light the spinner to hit first, then light the right orbit to hit second
  * Once both are hit, light both ramps
  * Hit both ramps (in either order) to complete the mode
  * Play a semi-random sound on each hit (dependent on which squadmates are recruited)
* **[Samara](recruitsamara/config/recruitsamara.yaml)** - Chase Morinth
  * All standup targets start lit, all lanes are off
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
  * When the ramps counter reaches a certain value, light the orbit shots
    * Counter needs 3 hits the first time this mode is played
    * Counter only needs 1 hit on subsequent play attempts
  * Continue hitting ramps to build value
  * Hit either orbit to complete the mode and collect the value
* **[Zaeed](recruitzaeed/config/recruitzaeed.yaml)** - Assault the Refinery
  * Light two shots, one red and one blue, to indicate two "paths" for the player
  * After a path is chosen, light a set of shots and count their hits
  * When a lit shot is hit, add some time to the timer and play a sound based on the chosen path
  * Complete the mode when the counter reaches a specified value
  * Clear the chosen path and reset the counter when the mode restarts

### Story Missions
Story missions are the mini-wizard and final wizard modes of the game, and are
unlocked by completing missions. Most missions are selected from the Mission Select
menu, but some start automatically when certain conditions are met.

#### Collector Ship
The Collector Ship mission is available after 4 squadmates are recruited, and
is started from the mission select screen. Once enabled, no other missions can be
selected and the Collector Ship can not be bypassed.

The Collector Ship consists of a "base" mode that runs underneath and manages the three "phase" modes,
which cycle through as long as the player is able to maintain them. The mode (and its
corresponding achievement) are considered "complete" if the player finishes the third phase. Prior
to completion the mode will play until the player's turn ends, but if the player beats the third
phase then the mode will stop when only one ball remains.

* **[Base mode](collectorship_base/config/collectorship_base.yaml)**
  * Start the mini-wizard mode and manage the transition between phases
  * Handle common sound files shared between phases
  * Start a multiball and add balls on certain events
* **[Ambush Phase](collectorship_ambush/config/collectorship_ambush.yaml)**
  * Light all shots and count each one's hit
  * Add a ball (up to a maximum number) when a lit shot is hit
  * Play a sound when only one lit shot remains
  * Complete the phase when all lit shots are hit
* **[Husk Phase](collectorship_husk/config/collectorship_husk.yaml)**
  * Start a timer and light all standup targets
  * Hit a standup to light a random lane shot and build value
  * Hit a lane to collect and reset the built values
  * Store the total sum of all values built/collected
  * Play sounds depending on which squadmates have been recruited
  * End the phase automatically when the timer runs out
* **[Praetorian Phase](collectorship_praetorian/config/collectorship_praetorian.yaml)**
  * Start a countdown timer for the Praetorian's "attack"
  * Light one random lane and one random bank
  * Hit any lit shot to reset the countdown and light new random shots
  * If the "attack" timer runs out, play a show and disable one flipper
  * Re-enable the flipper by hitting a lit shot
  * Count the hit shots to complete the mode and return to the Ambush phase
  * If the "attack" timer runs out a second time, regress back to the Husk phase

This mode can only be played once.

#### Derelict Reaper
The [Derelict Reaper mode](derelictreaper/config/derelictreaper.yaml) can be selected from the Misson Select when the player reaches level 8
(by recruiting squadmates and/or completing other missions), but it does not have
to be played immediately. The player can continue recruiting and doing
other missions before they choose to play the Derelict Reaper.
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
The [Normandy Attack mode](normandyattack/config/normandyattack.yaml) is driven from a pop bumper counter that starts counting down immediately
after the Derelict Reaper mode is played (regardless of whether the achievement
was completed). When the counter reaches zero, all other modes stop and the
Normandy Attack begins immediately.
  * Override all light, sound, and slide plays to simulate machine shutdown
  * Shut off flippers and force a ball drain while a show plays
  * Enable a secret ball save to resume play without costing a player ball
  * Stagger the drain, ball save, trough eject, and auto-plunge events based on sound playback
  * Light a pre-set sequence of shots to hit for completion
  * Use sequence shots to detect ramp shot failures
  * Light an outlane ball save on each shot completion

#### Suicide Mission
This is the final wizard mode of the game, a sequence of five modes with variable
behavior depending on which missions have been completed (and which squadmates
recruited). It's under active development so the documentation is limited to
the in-config comments.
  * **[Omega 4 Relay](suicide_omegarelay/config/suicide_omegarelay.yaml)**
    * Collect all the shots in this timed multiball, and complete the set to receive an Extra Ball. The mode automatically ends
      when all the shots are hit, all the balls drain, or the timer runs out. There is no "failure" and the next phase begins automatically.
  * **[Infiltration](suicide_infiltration/config/suicide_infiltration.yaml)**
    * It's a race against time to get through the Collector Base. Choose a tech specialist and hit a series of shots to lead them
      through the ventilation shaft. Each successful hit resets the timer and completing the full sequence finishes the mode. If the
      timer runs out, the specialist is killed and the mode must be re-started (with a new specialist) from the ball lock shot.
  * **[the Long Walk](suicide_longwalk/config/suicide_longwalk.yaml)**
    * This is a high-pressure and intense mode where speed and precision are required. Choose a biotic specialist and hit a series
      of shots to navigate to the central chamber, with each successful shot resetting the timer. Hitting an incorrect shot knocks 1/3rd
      of the remaining time away, so don't stray! The more biotics you have in your squad, the more likely a secondary shot
      will light for a given step of the sequence. If the timer runs out a random squadmate is killed and the mode must be restarted from
      the ball lock. If the ball drains, the specialist is killed and a new one must be selected on the next ball.
    * This mode uses [custom mode code](suicide_longwalk/code/suicide_longwalk.py) to handle the random lighting of shots (i.e. no shot
      can be lit twice in a row) and the calculation of "bonus" shots lighting based on the squad composition.
  * **[Destroy the Tubes](suicide_tubes/config/suicide_tubes.yaml)**
    * This mode lights four shots to be hit to destroy the structural support tubes, and a final shot after they are completed.
  * **[the Final Battle](suicide_final/config/suicide_final.yaml)**
    * The underlying mode for the final battle is a helper mode to handle the transitions between the following two phases, to ensure
      that sounds and shows started at the end of one can proceed through to the next. It also manages the damage value and attack
      damage to the Reaper, for knowing when to continue cycling the phases and when to proceed to the next mode.
    * ***[Collector Phase](suicide_platforms/config/suicide_platforms.yaml)***
      * This is a free-shooting multiball phase with all shots lit to build a "damage" jackpot value. Each shot adds hurryup time (up to
      a maximum playtime of 60 seconds) and completing all shots resets them to be collected again. When the hurryup expires, the damage
      value is carried over to the next phase:
    * ***[Human Reaper Phase](suicide_humanreaper/config/suicide_humanreaper.yaml)***
      * This phase is a timed shot with serious risk. One random shot is lit, hitting it deals the Reaper some "damage" based on the
        built value from the previous phase. There is a short timer while the Reaper's cannon charges, and then another when prepares
        to fire.
      * At the point of cannon firing, the flippers are temporarily disabled and the ball may drain. During the firing countdown, a
        shot to any ball hold or ball lock will keep the ball save ("in cover") until after the cannon fires and flipper power is
        restored. An audio cue helps inform the player that they should take cover.
      * After the player damages the Reaper (or enough time has passed), this phase ends and the game returns to the *Collector Phase*
        so the player can build a new damage value.
      * After the Reaper takes enough damage, it is destroyed and the game progresses to the final phase.
  * **the End Run / Escape**

In short, the Suicide Mission is an inordinately complex series of play modes and helper modes. The modes above are all handled by way
of these helper modes:

  * **[Suicide Base Mode](suicide_base/config/suicide_base.yaml)**
    * This mode is the heart of the Suicide Mission, and it runs whenever the mission is in play. It's responsible for knowing which
      modes to start, how to transition between them, how to delay ball_eject events during specialist selection and forced drains,
      and how to handle the success or failure of the various phases.
    * This mode includes [custom mode code](suicide_base/code/suicide_base.py) specifically for killing squadmates. Different scenarios
      determine which squadmates can (or cannot) be killed at a given time; this custom code is able to randomly (or explicitly) choose
      one and handle the appropriate events/variables. It also checks whether the Suicide Mission can still be completed based on the
      squad composition, and ends the Suicide Mission if there are not enough (or properly-talented) squadmates to proceed.
  * **[Suicide Huddle Mode](suicide_huddle/config/suicide_huddle.yaml)**
    * This mode is the transition between phases, and is used to play shows and delay ball eject/drain/save events until after the
      shows are completed. This mode is also a Carousel mode for selecting a specialist.
    * This mode includes [custom mode code](suicide_huddle/code/suicide_huddle.py) for handling the specialist selection, which
      must display a list of squadmates based on whether a mate is recruited, still alive, and has technical or biotic skills.
  * **[Suicide Restart](suicide_restart/config/suicide_restart.yaml)**
    * This mode is used when the timer during _Infiltration_ or _the Long Walk_ expires and a squadmate is killed. Unlike ball-drain-kills,
      which automatically show the specialist selection screen on the next ball, timer-expiration-kills require the player to
      hit the ball lock to start the mode again.

### Side Missions
Side missions provide additional gameplay during the course of collecting
recruitment missions, and are unlocked by hitting various targets/banks/bumpers.

#### Lair of the Shadow Broker
This is a series of unlockable modes governed by the [global shadowbroker mode](global/config/global_shadowbroker.yaml).
The global mode handles the tracking/lighting of dropbank hits to enable the
series of mini-wizard modes:
* **[Vasir Chase](shadowbroker_chase/config/shadowbroker_chase.yaml)** is a
typical, timed, follow-the-shots-sequence with a pre-determined set of shots.
  * Light a shot and advance through a specific order of shots using `hit_events` and `enable_events`
  * Play a progression of success sounds as the lit shots are hit
  * Play a randomization of wrong-way sounds when the wrong shots are hit
  * Don't end the ball on drain, instead end the mode and return to the normal playfield
  * If the player fails, restart them one shot back from where they left off
* **[Vasir Combat](shadowbroker_vasir/config/shadowbroker_vasir.yaml)** is a
follow-the-shot mode where the player must repeatedly hit a shot that "jumps"
around the playfield
  * Define a sequence of shots in a shot_group with a rotation order
  * Light a "target" shot with a profile state and start a shot rotation timer
  * If the timer runs out, rotate the target to a different shot
  * If the target is hit: reset the timer, advance the profile state, and rotate the
  target to a different shot
    * *(this logic is way more complex than you'd think)*
  * Complete the mode by hitting the target on its final profile state (3x hits total)
* **[Hagalaz Ship](shadowbroker_hagalaz/config/shadowbroker_hagalaz.yaml)**
  * Define a group of shots and randomly light one every 8 seconds
  * Hit a lit shot to advance a counter
  * Use playfield lighting to indicate standups "charging up" over 10s
  * Hit a "charged" standup to count hits on the shots to either side (if they're lit)
  * Stop all timers and charging when the lit-shot-counter completes
  * Light a special *ball_hold* shot to finish the mode
* **[Boss Combat](shadowbroker_boss/config/shadowbroker_boss.yaml)**

#### Multiballs
There are two multiball modes, both of which are lit and locked in the same way
via the [global multiball handler](global/config/global_multiball.yaml). Overlord
is the multiball mode available prior to the Collector Ship mission, and Arrival
is available after.
* **[Project Overlord](overlord/config/overlord.yaml)** is a typical multiball that will run as long as there are multiple balls in play.
  * Light all lanes and start a hurryup timer
  * Hit any lane to enable a "jackpot" shot, build the hurryup value, and add time to the timer
  * Continue hitting lit lanes to build more value; hit the jackpot to collect
  * After each jackpot collection, it takes an additional lane shot to re-light
  * Collect 3 jackpots to complete the mode and the achievement
  * If the timer runs out, all lane shots "freeze" and must be reset
  * The mode ends when the balls drain down to one
* **[Arrival](arrival/config/arrival.yaml)** is a frenzy multiball that runs in phases.
  * Light a group of lanes and start a frenzy counter
  * Hitting any lit lane switches to a different group of lanes
  * Each hit switches between the two groups until all lanes are hit; then it all resets
  * Throughout this, every switch hit counts towards the frenzy
  * When the frenzy limit is completed, the lanes turn off and the ball lock enables
  * Each ball locked awards the jackpot of the value built from lanes
  * If the multiball drains to one ball, the jackpot lock is lit immediately

* **[N7 Assignments](n7_assignments/config/n7_assignments.yaml)** are single-shot modes that
are started automatically each time the pop bumper count is completed.
  * Light a random "mission" shot through `random_event_player`
  * Display a dynamic value on a slide using `event_player` arguments
  * Set a hurryup value on a timer and make a text widget show it ticking down
  * Award the hurryup value if the lit shot is hit
  * End the mode if the timer runs out

  * **[Firewalker](firewalker/config/firewalker.yaml)** is a series of modes that are lit from lanes on the field. Any lane not lit with a squadmate will progress with three hits (red, orange, green) to start the next Firewalker level
   * Each Firewalker level is a mode that runs on a timer and requires three lane shots to complete
   * Finishing a Firewalker level "completes" the lane that started it
   * The rules for which lanes are lit increase the difficulty for each level that has been completed
   * Completing all five Firewalker levels (i.e. from all five lanes) lights the Prothean Base multiball

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
* **[Base](base/config/base.yaml)** handles the fundamental gameplay and exists
beneath all other modes. It handles the transitions between *global* and various
wizard modes, and is responsible for starting/stopping modes when balls start and
end.
* [Medigel](base/config/base_medigel.yaml) handles a special outlane ball save that can
be enabled by events throughout the game and will save one outlane drain (if no other
ball saves are active).

#### Global
* **[Global Base](global/config/global.yaml)** handles the transitions between *field* and various mission modes, as well as common gameplay behaviors that exists in non-wizard play.
* [Global Multiball](global/config/global_multiball.yaml) handles the lighting and lock-enabling of multiballs, since both Overlord and Arrival multiball modes use the
same lighting/locking behavior.
  * Use achievement states to determine which multiball mode is being advanced
  * Enable a "light lock" shot on two hitbanks
  * Hit either hitbank to disable the "light" shot and enable the "lock" shot
  * Hit the lock shot to lock a ball, play a sound and slide, and re-enable the light shot
  * Lock three balls to start the appropriate multiball mode
  * After a multiball has been played, it can be lit/locked again but *both* hitbanks must be hit to light the lock.
* [Global Planets](global/config/global_planets.yaml) handles the pop bumper and top lane
behaviors, including multipliers and countdown awards.
* [Global Recruit](global/config/global_recruit.yaml) handles the lighting and tracking of
recruitment shots, allowing players to advance towards recruitment missions and playing
sounds/slides when those missions are completed. It also handles a common ball save
that runs when any recruit mission starts.
* [Global Shadow Broker](global/config/global_shadowbroker.yaml) handles the dropbank hits
that progress towards the various Shadow Broker modes.
  * Track dropbank completions and play a specific sound on each drop
  * Light up to three playfield lights to indicate the dropbank progress
  * Complete three dropbanks to enable the chase mode/achievement
  * While the chase is enabled, completing the dropbank starts the chase mode
  * After the chase is completed, the ball hold is enabled to start the vasir mode
  * After vasir is completed, the dropbank completion counting starts again
  * On the next third completion, the hagalaz mode/achievement is enabled
  * While hagalaz is enabled, completing the drapbank starts the hagalaz mode
  * After hagalaz is completed, the ball hold starts the boss mode
  * After the boss is completed, additional dropbanks award bonus points

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


