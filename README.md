# 🔥 AFIRE Fireplace Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://hacs.xyz)  
[![home-assistant](https://img.shields.io/badge/Home%20Assistant-Custom%20Integration-41BDF5?style=for-the-badge&logo=home-assistant&logoColor=white)](https://www.home-assistant.io/)  
[![license](https://img.shields.io/github/license/cristianomeda/afire_fireplace?style=for-the-badge)](LICENSE)

Control your **AFIRE water vapor fireplaces** directly in [Home Assistant](https://www.home-assistant.io/).  
👉 Official AFIRE website: [https://www.a-fireplace.com/](https://www.a-fireplace.com/)

---

## ⚠️ Disclaimer

This integration is an **independent community project**.  
It is **not affiliated with, endorsed, or supported by AFIRE**.  

- Use at your own risk.  
- AFIRE may change their API at any time, which could break this integration.  
- Provided **"as is" with no warranties**.  
- Please do not contact AFIRE support about this integration.

---

## ✨ Features

- 🔥 Control **fireplace power, flame height & speed**  
- 💡 Switch **Amber LEDs** and **RGB LEDs** independently  
- 🎨 Select **15 preset RGB colors** (arranged like the physical remote)  
- ✨ Trigger **lighting effects** (Smooth, Fade 1, Fade 2)  
- 🏠 Works with **multiple fireplaces** in one account  
- 📂 Full integration with HA **devices & areas**  
- 🔒 **Strict Mode** safety:  
  - If the fireplace is **OFF**, you cannot adjust flame, LEDs, colors, or effects.  
  - Commands are ignored and logged as warnings.  

---

## 📦 Installation

### Via HACS (recommended)
1. In HACS, add this repo as a **Custom Repository**.  
2. Search for **AFIRE Fireplace** and install.
3. Restart Home Assistant.  

### Manual
1. Copy the `afire` folder into your `custom_components` directory:  
   ```
   custom_components/afire/
   ```
2. Restart Home Assistant. 

---

## 🔑 Setup

1. Go to **Settings → Devices & Services → Add Integration**.  
2. Search for **AFIRE**.  
3. Enter your AFIRE **account credentials**.  
4. HA will discover all your fireplaces.  
5. Assign each fireplace a **name and room**.  

---

## 📸 Example UI

Here’s an example dashboard layout that mimics the **look and feel of the AFIRE remote control**:  

![AFIRE UI Example](./images/Afire-UI-Card.png)

This layout uses **Mushroom cards, RGB Light cards, and Buttons**.

---

## 🛠 Example Lovelace Configuration

```yaml
# Power switch
type: tile
entity: switch.fireplace_power
features_position: bottom
vertical: false
grid_options:
  columns: 12
  rows: 1
icon: mdi:power
hide_state: false

# Flame height
type: custom:mushroom-number-card
entity: number.fireplace_flame_height
name: Flame Height
layout: horizontal
icon_color: amber
icon: mdi:fire

# Flame speed
type: custom:mushroom-number-card
entity: number.fireplace_flame_speed
name: Flame Speed
layout: horizontal
icon_color: light-blue
icon: mdi:fan

# LEDs and color presets
type: entities
show_header_toggle: false
entities:
  - entity: switch.fireplace_amber_leds
    name: Amber LEDs
  - entity: switch.fireplace_rgb_leds
    name: RGB LEDs
  - type: custom:rgb-light-card
    entity: light.fireplace_colors
    size: 60
    justify: around
    colors:
      - rgb_color: [198, 50, 38]
      - rgb_color: [99, 152, 74]
      - rgb_color: [88, 85, 132]
  - type: custom:rgb-light-card
    entity: light.fireplace_colors
    size: 60
    justify: around
    colors:
      - rgb_color: [232, 61, 42]
      - rgb_color: [168, 201, 65]
      - rgb_color: [108, 110, 173]
  - type: custom:rgb-light-card
    entity: light.fireplace_colors
    size: 60
    justify: around
    colors:
      - rgb_color: [232, 89, 21]
      - rgb_color: [144, 182, 164]
      - rgb_color: [117, 78, 107]
  - type: custom:rgb-light-card
    entity: light.fireplace_colors
    size: 60
    justify: around
    colors:
      - rgb_color: [232, 154, 41]
      - rgb_color: [125, 174, 190]
      - rgb_color: [168, 99, 122]
  - type: custom:rgb-light-card
    entity: light.fireplace_colors
    size: 60
    justify: around
    colors:
      - rgb_color: [249, 234, 37]
      - rgb_color: [90, 159, 218]
      - rgb_color: [196, 103, 144]

# Effects
type: horizontal-stack
cards:
  - type: button
    show_name: false
    icon: mdi:scent
    tap_action:
      action: call-service
      service: light.turn_on
      target:
        entity_id: light.fireplace_colors
      data:
        effect: Smooth
    icon_height: 40px

  - type: button
    show_name: false
    icon: mdi:animation
    tap_action:
      action: call-service
      service: light.turn_on
      target:
        entity_id: light.fireplace_colors
      data:
        effect: Fade 1
    icon_height: 40px

  - type: button
    show_name: false
    icon: mdi:animation-outline
    tap_action:
      action: call-service
      service: light.turn_on
      target:
        entity_id: light.fireplace_colors
      data:
        effect: Fade 2
    icon_height: 40px
```
---

## 📝 Roadmap

- [ ] Local control (bypass cloud)  
- [ ] More robust effect/color sync from API  
- [ ] Additional models (if AFIRE expands lineup)  

---

## 🙌 Credits

- Built by the community for the community ❤️  
- Inspired by the AFIRE remote and app.

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).