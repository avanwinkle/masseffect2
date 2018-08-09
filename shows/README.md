# Show Presets

Here are a few preset shows for use in shared profiles, as well as the more orchestrated game event shows. This readme outlines how to use some of the presets in different game modes.

## LED Rings

While MPF supports LED sequences in "strip" and "ring" form, there's no easy way to utilize the sequence to produce patterns. Here are a few shows that utilize a ring of 16 LEDs to light shots:

* **[Bounce Quad](led_16_bounce_quad.yaml)** creates four points around the circle (1px on smaller rings, up to 3px on large rings) and bounces the points left and right

* **[Chase Duo](led_16_chase_duo.yaml)** creates two tails (a few pixels fully lit and then fading down behind) opposite each other and moves the two around the ring, creating a spinning effect as though the two were chasing each other

* **[Countdown](led_16_countdown.yaml)** lights all the pixels in the ring and then starts turning pixels off in counterclockwise order, creating the appearance of a timer running down

### Sample usage

The LED Ring shows use three tokens: 
* `ledring` for the led device (could be light_ring or light_stripe)
* `color` for the fully-lit color value
* `fade` for the fade between states

```
light_stripes:
  test_ring_16:
    debug: true
    number_start: 0
    count: 16
    light_template:
      platform: fadecandy
      type: grb

show_player:
  some_timer_started:
    led_16_countdown:
      speed: 1
      show_tokens:
        ledring: test_ring_16
        color: 009900
        fade: 60ms
```