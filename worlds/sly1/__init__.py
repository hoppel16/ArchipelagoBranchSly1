import random
import logging
from typing import Dict, Any, Mapping
from BaseClasses import MultiWorld, Item, ItemClassification, Tutorial
from worlds.AutoWorld import World, CollectionState, WebWorld
from worlds.sly1.Items import item_table, create_itempool, create_item, event_item_pairs, sly_episodes
from worlds.sly1.Locations import get_location_names, get_total_locations, did_avoid_early_bk, generate_bottle_locations, generate_minigame_locations
from worlds.sly1.Options import Sly1Options
from worlds.sly1.Regions import create_regions
from worlds.sly1.Types import Sly1Item, EpisodeType, episode_type_to_name, episode_type_to_shortened_name
from worlds.sly1.Rules import set_rules
from worlds.LauncherComponents import (
    Component,
    Type,
    components,
    launch_subprocess,
    icon_paths,
)
from Options import OptionError
from worlds.sly1.Sly1Client import launch_client

def run_client():
    launch_subprocess(launch_client, name="Sly1Client")

#icon_paths["sly1_ico"] = f"ap:{__name__}/icon.png"
components.append(
    Component("Sly 1 Client", func=run_client, component_type=Type.CLIENT)
)

class Sly1Web(WebWorld):
    theme = "ocean"
    tutorials = [Tutorial(
        "Multiworld Setup Guide",
        "A guide to setting up Sly Cooper and the Thievius Raccoonus for Archipelago. "
        "This guide covers single-player, multiworld, and related software.",
        "English",
        "setup_en.md",
        "setup/en",
        ["Nep"]
    )]

class Sly1World(World):
    """
    Sly Cooper and the Thievius Raccoonus is a action-stealth game set in a cartoony cel-shaded world.
    Avenge your father and take back the pages of the Thievius Raccoonus from the Fiendish Five!
    """

    game = "Sly Cooper and the Thievius Raccoonus"
    item_name_to_id = {name: data.ap_code for name, data in item_table.items()}
    location_name_to_id = get_location_names()
    options_dataclass = Sly1Options
    options = Sly1Options
    web = Sly1Web()

    # this is how we tell the Universal Tracker we want to use re_gen_passthrough
    @staticmethod
    def interpret_slot_data(slot_data: Dict[str, Any]) -> Dict[str, Any]:
        return slot_data

    # and this is how we tell Universal Tracker we don't need the yaml
    ut_can_gen_without_yaml = True

    def __init__(self, multiworld: MultiWorld, player: int):
        super().__init__(multiworld, player)

    def generate_early(self) -> None:
        # implement .yaml-less Universal Tracker support
        if hasattr(self.multiworld, "generation_is_fake"):
            if hasattr(self.multiworld, "re_gen_passthrough"):
                # I'm doing getattr purely so pylance stops being mad at me
                re_gen_passthrough = getattr(self.multiworld, "re_gen_passthrough")

                if "Sly Cooper and the Thievius Raccoonus" in re_gen_passthrough:
                    slot_data = re_gen_passthrough["Sly Cooper and the Thievius Raccoonus"]
                    self.options.UnlockClockwerk.value = slot_data["UnlockClockwerk"]
                    self.options.FastClockwerk.value = slot_data["FastClockwerk"]
                    self.options.RequiredBosses.value = slot_data["RequiredBosses"]
                    self.options.MaxPages.value = slot_data["MaxPages"]
                    self.options.RequiredPages.value = slot_data["RequiredPages"]
                    self.options.StartingEpisode.value = slot_data["StartingEpisode"]
                    self.options.IncludeHourglasses.value = slot_data["IncludeHourglasses"]
                    self.options.HourglassesRequireRoll.value = slot_data["HourglassesRequireRoll"]
                    self.options.AvoidEarlyBK.value = slot_data["AvoidEarlyBK"]
                    self.options.ExcludeMinigames.value = slot_data["ExcludeMinigames"]
                    self.options.MinigameCaches.value = slot_data["MinigameCaches"]
                    self.options.LocationCluesanityBundleSize.value = slot_data["LocationCluesanityBundleSize"]
                    self.options.ItemCluesanityBundleSize.value = slot_data["ItemCluesanityBundleSize"]
                    self.options.CutsceneSkip.value = slot_data["CutsceneSkip"]
                    self.options.TrapChance.value = slot_data["TrapChance"]
                    self.options.IcePhysicsTrapWeight.value = slot_data["IcePhysicsTrapWeight"]
                    self.options.SpeedChangeTrapWeight.value = slot_data["SpeedChangeTrapWeight"]
                    self.options.InvisibilityTrapWeight.value = slot_data["InvisibilityTrapWeight"]
                    self.options.BallTrapWeight.value = slot_data["BallTrapWeight"]
            return

        starting_episode = EpisodeType(self.options.StartingEpisode)
        starting_episode_long = episode_type_to_name[starting_episode]
        starting_episode_short = episode_type_to_shortened_name[starting_episode]

        # Starting Episode - please clean this up oml
        if starting_episode_long == "All":
            for episode in sly_episodes.keys():
                self.multiworld.push_precollected(self.create_item(episode))
        else:
            self.multiworld.push_precollected(self.create_item(starting_episode_long))

        # Avoid Early BK
        if did_avoid_early_bk(self):
            if starting_episode_long == "All":
                starting_episode_short = episode_type_to_shortened_name[EpisodeType(random.randrange(1, 4))]
                self.random_episode = starting_episode_short
            self.multiworld.push_precollected(self.create_item(f'{starting_episode_short} Key'))

    def create_regions(self):
        create_regions(self)

        if self.options.LocationCluesanityBundleSize.value > 0:
            generate_bottle_locations(self, self.options.LocationCluesanityBundleSize.value)

        if self.options.LocationCluesanityBundleSize.value == 0 and self.options.ItemCluesanityBundleSize.value > 0:
            logging.warning(
                f"{self.player}: Cannot have item bundles without location bundles. Setting location bundle size to item bundle size.")
            self.options.LocationCluesanityBundleSize.value = self.options.ItemCluesanityBundleSize.value
            generate_bottle_locations(self, self.options.LocationCluesanityBundleSize.value)
        
        generate_minigame_locations(self, self.options.MinigameCaches.value)

    def create_items(self):
        itempool = create_itempool(self)
        self.multiworld.itempool.extend(itempool)
        location_count = len(self.multiworld.get_unfilled_locations(self.player))
        item_count = len(itempool)
        for event, item in event_item_pairs.items():
            event_item = Sly1Item(item, ItemClassification.progression_skip_balancing, None, self.player)
            self.multiworld.get_location(event, self.player).place_locked_item(event_item)
        if location_count - item_count >= 0:
            filler = [self.create_filler() for _ in range(location_count - item_count)]
            self.multiworld.itempool.extend(filler)
        else:
            self.handle_not_enough_locations(item_count - location_count)

    def handle_not_enough_locations(self, count):
        """Check the available location and items counts, raise OptionErrors to warn the player of too few locations"""
        option_list: list[str] = []
        if self.options.LocationCluesanityBundleSize == 0:
            option_list.append("Location Cluesanity Bundle Size")
        if self.options.MinigameCaches == 0:
            option_list.append("Minigame Caches")
        if not option_list:
            option_list: str = "dunno"  # ¯\_(''/)_/¯
        message = f"Not enough location options enabled! {count} items have nowhere to be placed."
        message += f"Consider adjusting some of the following options: {option_list}"
        raise OptionError(message)
    set_rules = set_rules

    def create_item(self, name: str) -> Item:
        return create_item(self, name)

    def get_options_as_dict(self) -> Dict[str, Any]:
        return self.options.as_dict(
            "UnlockClockwerk",
            "RequiredBosses",
            "MaxPages",
            "RequiredPages",
            "FastClockwerk",
            "StartingEpisode",
            "IncludeHourglasses",
            "HourglassesRequireRoll",
            "AvoidEarlyBK",
            "LocationCluesanityBundleSize",
            "ItemCluesanityBundleSize",
            "CutsceneSkip",
            "ExcludeMinigames",
            "MinigameCaches",
            "TrapChance",
            "IcePhysicsTrapWeight",
            "SpeedChangeTrapWeight",
            "InvisibilityTrapWeight",
            "BallTrapWeight",
        )

    def fill_slot_data(self) ->Mapping[str, object]:
        slot_data = self.get_options_as_dict()

        return slot_data

    def collect(self, state: "CollectionState", item: "Item") -> bool:
        return super().collect(state, item)
    
    def remove(self, state: "CollectionState", item: "Item") -> bool:
        return super().remove(state, item)