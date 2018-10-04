# ME2 Core Configuration

The core configuration is divided into multiple files, for ease of use, and may be subdivided more in the future.

* **[config.yaml]** handles the MPF configuration (modes, player variables, mpf-mc)
* **[hardware.yaml]** handles the Spike Game of Thrones hardware (switches, coils, lights, devices)
* **[keyboard.yaml]** handles key bindings for convenience during testing.

### Atomic Widget Styles

To facilitate development on an existing Stern SPIKE system while planning forward
to a custom machine body, display widgets should use design-agnostic style names.
This allows each hardware platform to define its own widget styles (low-res
pixel sizing for the SPIKE DMD and high-res antialiased sizing for the custom
LCD).

This section outlines the style names shared by each platform and the uses for each.


#### Header Large
* Single-player score
* Mission names
