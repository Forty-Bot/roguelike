#!/usr/bin/python
import libtcodpy as libtcod
import math
import textwrap

SCREEN_WIDTH	= 80
SCREEN_HEIGHT	= 50

MAP_WIDTH		= 80
MAP_HEIGHT		= 45

LIMIT_FPS		= 20

ROOM_MAX_SIZE	= 10
ROOM_MIN_SIZE	= 6
MAX_ROOMS		= 30

FOV_ALGO		= libtcod.FOV_PERMISSIVE_8
FOV_LIGHT_WALLS	= True
TORCH_RADIUS	= 80

BAR_WIDTH		= 20
PANEL_HEIGHT	= 5
PANEL_Y			= SCREEN_HEIGHT - PANEL_HEIGHT

MONSTER_CHANCE	= 20
ITEM_CHANCE		= 20
MAX_ROOM_OBJECTS= 5

MSG_X			= BAR_WIDTH + 2
MSG_WIDTH		= SCREEN_WIDTH - BAR_WIDTH - 2
MSG_HEIGHT		= PANEL_HEIGHT - 1

INVENTORY_WIDTH	= 50

SALVE_HEAL		= 5

color_dark_wall = libtcod.Color(0, 0, 100)
#color_light_wall = libtcod.Color(130, 110, 50)
color_light_wall = color_dark_wall + libtcod.dark_gray
color_dark_ground = libtcod.Color(50, 50, 150)
#color_light_ground = libtcod.Color(200, 180, 50)
color_light_ground = color_dark_ground + libtcod.dark_grey

class Object:  #generic object
	def __init__(self, x, y, char, name, color, blocks=False,
		fighter=None, ai=None, item=None):
		self.x = x
		self.y = y
		self.char = char
		self.name = name
		self.color = color
		self.blocks = blocks
		self.fighter = fighter
		self.ai = ai
		self.item = item
		if self.fighter:
			self.fighter.owner = self
		if self.ai:
			self.ai.owner = self
		if self.item:
			self.item.owner = self

	def move(self, dx, dy):  #move by a given amount
		if not is_blocked(self.x + dx, self.y + dy):
			self.x += dx
			self.y += dy

	def draw(self):  #draw the object
		if libtcod.map_is_in_fov(fov_map, self.x, self.y):
			libtcod.console_set_default_foreground(con, self.color)
			libtcod.console_put_char(con, self.x, self.y, self.char, libtcod.BKGND_NONE)

	def clear(self):  #clear yourself
		libtcod.console_put_char(con, self.x, self.y, ' ', libtcod.BKGND_NONE)

	def move_toward(self, target_x, target_y):
		dx = target_x - self.x
		dy = target_y - self.y
		distance = math.sqrt(dx ** 2 + dy ** 2)

		dx = int(round(dx / distance))
		dy = int(round(dy / distance))
		self.move(dx, dy)

	def distance_to(self, other):
		dx = other.x - self.x
		dy = other.y - self.y
		return math.sqrt(dx ** 2 + dy ** 2)

	def send_to_back(self):
		global objects
		objects.remove(self)
		objects.insert(0, self)

class Fighter:  #an object which fights
	def __init__(self, hp, defense, power, death_function=None):
		self.max_hp = hp
		self.hp = hp
		self.defense = defense
		self.power = power
		self.death_function = death_function

	def take_damage(self, damage):
		self.hp -= damage
		if self.hp <= 0:
			function = self.death_function
			if function is not None:
				function(self.owner)

	def attack(self, target):
		if not target.fighter:  #If the target isn't a fighter, return
			return
		if target.fighter.hp <= 0:
			return
		damage = self.power - target.fighter.defense
		if damage > 0:
			message('The '+self.owner.name.capitalize()+' attacks '+target.name+' for '+str(damage)+' damage!')
			target.fighter.take_damage(damage)
		else:
			message('The '+self.owner.name.capitalize()+' attacks '+target.name+' but does no damage!')

class BasicMonster:  #Ai stuff
	def take_turn(self):
		monster = self.owner
		if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):  #if the player can see the monster
			if monster.distance_to(player) >= 2:
				monster.move_toward(player.x, player.y)
			elif player.fighter.hp > 0:
				monster.fighter.attack(player)

class Item:  #Pick-uppable
	def __init__(self, desc=None, on_pickup=None, on_drop=None, on_use=None, stats=None):
		self.desc = desc
		self.on_pickup = on_pickup
		self.on_drop = on_drop
		self.on_use = on_use
		self.stats = stats
		if stats:
			self.stats.owner = self

	def pick_up(self):
		global player

		if(len(inventory) >= 26):
			message('Inventory full')
		else:
			inventory.append(self.owner)
			objects.remove(self.owner)

			message('You picked up a '+self.owner.name+'!', libtcod.green)

			function = self.on_pickup
			if function is not None:
				function(self)

			if self.stats:
				player.fighter.hp += int((1.0 * player.fighter.hp / player.fighter.max_hp) * self.stats.dhp)
				player.fighter.max_hp += self.stats.dhp
				player.fighter.defense += self.stats.ddefense
				player.fighter.power += self.stats.dpower


	def drop(self):
		global player

		inventory.remove(self.owner)
		self.owner.x = player.x
		self.owner.y = player.y
		objects.append(self.owner)
		self.owner.send_to_back()

		message(self.owner.name.capitalize()+' dropped.', libtcod.green)

		function = self.on_drop
		if function is not None:
			function(self)

		if self.stats:
				player.fighter.hp -= int((1.0 * player.fighter.hp / player.fighter.max_hp) * self.stats.dhp)
				player.fighter.max_hp -= self.stats.dhp
				player.fighter.defense -= self.stats.ddefense
				player.fighter.power -= self.stats.dpower

	def use(self):
		function = self.on_use
		if function is None:
			message("You can't do that!")
		else:
			function(self)

class Stats:
	def __init__(self, dhp=0, ddefense=0, dpower=0):
		self.dhp = dhp
		self.ddefense = ddefense
		self.dpower = dpower

class Tile: #a tile on the map
	def __init__(self, blocked, opaque = None):
		self.explored = False
		self.blocked = blocked
		if opaque is None:  #By default, make it match blocked
			opaque = blocked
		self.opaque = opaque

class Rect:  #A rectange on the map
	def __init__(self, x, y, w, h):
		self.x1 = x
		self.y1 = y
		self.x2 = x + w
		self.y2 = y + h

	def center(self): #Find the center of a rect
		center_x = (self.x1 + self.x2) / 2
		center_y = (self.y1 + self.y2) / 2
		return (center_x, center_y)

	def intersect(self, other): #Returns true if two rects intersect
		return (self.x1 <= other.x2 and self.x2 >= other.x1 and
				self.y1 <= other.y2 and self.y2 >= other.y1)

def create_room(room):  #Create a room from a rectangle
	global map
	#make the rectangle tiles passable
	for x in range(room.x1 + 1, room.x2):
		for y in range(room.y1 + 1, room.y2):
			map[x][y].blocked = False
			map[x][y].opaque = False

def create_h_tunnel(x1, x2, y):  #Create a horizontal tunnel from (x1, y) to (x2, y)
	global map
	for x in range(min(x1, x2), max(x1, x2) + 1):
		map[x][y].blocked = False
		map[x][y].opaque = False

def create_v_tunnel(y1, y2, x):  #Create a vertical tunnel from (x, y1) to (x, y2)
	global map
	for y in range(min(y1, y2), max(y1, y2) + 1):
		map[x][y].blocked = False
		map[x][y].opaque = False

def make_map():
	global map

	map = [[ Tile(True)  #Tiles start out impassable/opaque
		for y in range(MAP_HEIGHT) ]
			for x in range(MAP_WIDTH) ]

	rooms = []
	num_rooms = 0

	for r in range(MAX_ROOMS):
		#Generate a room
		w = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
		h = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
		x = libtcod.random_get_int(0, 0, MAP_WIDTH - w - 1)
		y = libtcod.random_get_int(0, 0, MAP_HEIGHT - h - 1)

		#pdb.set_trace()

		new_room = Rect(x, y, w, h)

		failed =  False
		for other_room in rooms:
			if new_room.intersect(other_room):
				failed = True
				break

		if not failed:
			create_room(new_room)
			place_objects(new_room)

			(new_x, new_y) = new_room.center()

			#room_no = Object(new_x, new_y, chr(65+num_rooms), 'room number', libtcod.white)
			#objects.insert(0, room_no)

			if num_rooms == 0: #is this the first room?
				player.x = new_x  #set the player's coords to here
				player.y = new_y
			else:  #otherwise connect it to the previous room

				(prev_x, prev_y) = rooms[num_rooms-1].center()  #coords to the previous room

				if libtcod.random_get_int(0, 0, 1) == 1:
					create_h_tunnel(prev_x, new_x, prev_y)
					create_v_tunnel(prev_y, new_y, new_x)
				else:
					create_v_tunnel(prev_y, new_y, prev_x)
					create_h_tunnel(prev_x, new_x, new_y)

			rooms.append(new_room)
			num_rooms += 1



def render_all():
	global fov_recompute

	if fov_recompute:
		fov_recompute = False
		libtcod.map_compute_fov(fov_map, player.x, player.y, TORCH_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)

	for y in range(MAP_HEIGHT):  #Render tiles
		for x in range(MAP_WIDTH):
			wall = map[x][y].opaque
			visible = libtcod.map_is_in_fov(fov_map, x, y)
			if not visible:
				if map[x][y].explored:
					if wall:
						libtcod.console_set_char_background(con, x, y, color_dark_wall, libtcod.BKGND_SET)
					else:
						libtcod.console_set_char_background(con, x, y, color_dark_ground, libtcod.BKGND_SET)
			else:
				if wall:
					libtcod.console_set_char_background(con, x, y, color_light_wall, libtcod.BKGND_SET)
				else:
					libtcod.console_set_char_background(con, x, y, color_light_ground, libtcod.BKGND_SET)
				map[x][y].explored = True

	for object in objects:
		if object != player:
			object.draw()
	player.draw()

	libtcod.console_blit(con, 0, 0, MAP_WIDTH, MAP_HEIGHT, 0, 0, 0)

	#Panel
	libtcod.console_set_default_background(panel, libtcod.black)
	libtcod.console_clear(panel)
	y = 1
	for (line, color) in game_msgs:  #Messages
		libtcod.console_set_default_foreground(panel, color)
		libtcod.console_print_ex(panel, MSG_X, y, libtcod.BKGND_NONE, libtcod.LEFT, line)
		y += 1
	render_bar(1, 1, BAR_WIDTH, 'HP', player.fighter.hp, player.fighter.max_hp, libtcod.light_red, libtcod.darker_red)  #health
	libtcod.console_set_default_foreground(panel, libtcod.light_grey)
	libtcod.console_print_ex(panel, 1, 0, libtcod.BKGND_NONE, libtcod.LEFT, get_names_under_mouse())
	libtcod.console_set_default_foreground(panel, libtcod.white)
	libtcod.console_print_ex(panel, 1, 2, libtcod.BKGND_NONE, libtcod.LEFT, 'POW: '+str(player.fighter.power))
	libtcod.console_print_ex(panel, 1, 3, libtcod.BKGND_NONE, libtcod.LEFT, 'DEF: '+str(player.fighter.defense))
	libtcod.console_blit(panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)

def place_objects(room):

	for i in range(1, MAX_ROOM_OBJECTS):
		j = libtcod.random_get_int(0, 1, 100)

		if j < MONSTER_CHANCE:
			place_function = place_monster
		elif j < MONSTER_CHANCE+ITEM_CHANCE:
			place_function = place_item
		else:
			continue

		while True:
			x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
			y = libtcod.random_get_int(0, room.y1+1, room.y2-1)
			if not is_blocked(x, y):
				break

		place_function(x, y)

def place_monster(x, y):

	monster_type = libtcod.random_get_int(0, 1, 100)

	if monster_type < 50:
		fighter_component = Fighter(hp=10, defense=1, power=5, death_function=monster_death)
		ai_component = BasicMonster()
		monster = Object(x, y, 'd', 'dingo', libtcod.desaturated_amber, blocks=True, fighter=fighter_component, ai=ai_component)
	else:
		fighter_component = Fighter(hp=5, defense=3, power=3, death_function=monster_death)
		ai_component = BasicMonster()
		monster = Object(x, y, 'o', 'orc', libtcod.sepia, blocks=True, fighter=fighter_component, ai=ai_component)

	objects.append(monster)

def place_item(x, y):

	item_type = libtcod.random_get_int(0, 1, 100)

	if item_type < 25:
		item_component = Item(on_use=salve_use)
		item = Object(x, y, '!', 'healing salve', libtcod.green, item=item_component)
	elif item_type < 50:
		stats_component = Stats(dpower=1)
		item_component = Item(stats=stats_component)
		item = Object(x, y, ')', 'broadsword', libtcod.grey, item=item_component)
	elif item_type < 75:
		stats_component = Stats(dhp=5)
		item_component = Item(stats=stats_component)
		item = Object(x, y, '=', 'ring of health', libtcod.red, item=item_component)
	else:
		stats_component = Stats(ddefense=1)
		item_component = Item(stats=stats_component)
		item = Object(x, y, '=', 'ring of protection', libtcod.grey, item=item_component)

	objects.append(item)
	item.send_to_back()

def salve_use(self):
	remove = False

	if player.fighter.max_hp == player.fighter.hp:
		message('You are already fully healed!')
	else:
		player.fighter.hp += SALVE_HEAL
		if player.fighter.hp > player.fighter.max_hp:
			player.fighter.hp = player.fighter.max_hp
		inventory.remove(self.owner)

def player_death(player):
	global game_state
	message('You died.', libtcod.red)
	game_state = 'dead'


def monster_death(monster):
	message('The '+monster.name+' dies.', libtcod.orange)
	monster.char = '%'
	monster.blocks = False
	monster.fighter = None
	monster.ai = None
	monster.name = monster.name+' corpse'
	monster.send_to_back()

def is_blocked(x, y):
	if map[x][y].blocked:
		return True

	for object in objects:
		if object.blocks and object.x == x and object.y == y:
			return True

	return False

def player_move_or_attack(dx, dy):
	global fov_recompute

	x = player.x + dx
	y = player.y + dy

	target = None
	for object in objects:
		if object.x == x and object.y == y and object.fighter:
			target = object
			break

	if target is not None:
			player.fighter.attack(target)
	else:
		player.move(dx, dy)
		fov_recompute = True

def render_bar(x, y, total_width, name, value, maximum, bar_color, back_color):  #Render a bar
	bar_width = int(float(value) / maximum * total_width)

	#Render background
	libtcod.console_set_default_background(panel, back_color)
	libtcod.console_rect(panel, x, y, total_width, 1, False, libtcod.BKGND_SCREEN)

	#Render the bar
	libtcod.console_set_default_background(panel, bar_color)
	if bar_width > 0:
		libtcod.console_rect(panel, x, y, bar_width, 1, False, libtcod.BKGND_SCREEN)

	libtcod.console_set_default_foreground(panel, libtcod.white)
	libtcod.console_print_ex(panel, x + total_width / 2, y, libtcod.BKGND_NONE, libtcod.CENTER,
		name+': '+str(value)+'/'+str(maximum))

def message(message, color=libtcod.white):
	new_message_lines = textwrap.wrap(message, MSG_WIDTH)
	for line in new_message_lines:
		if len(game_msgs) == MSG_HEIGHT:
			del game_msgs[0]
		game_msgs.append( (line, color) )

def get_names_under_mouse():
	global mouse

	(x, y) = (mouse.cx, mouse.cy)

	names = [obj.name for obj in objects
		if obj.x == x and obj.y == y and libtcod.map_is_in_fov(fov_map, obj.x, obj.y)]

	names = ', '.join(names)  #now it's a comma seperated list!
	return names.capitalize()

def menu(header, options, width):
	if len(options) > 26:
		raise ValueError('A 27 option menu?  You *must* be joking.')

	#Calculate the height of the menu
	header_height = libtcod.console_get_height_rect(con, 0, 0, width, SCREEN_HEIGHT, header)
	height = len(options) + header_height

	window = libtcod.console_new(width, height)
	libtcod.console_set_default_foreground(window, libtcod.white)
	libtcod.console_print_rect_ex(window, 0, 0, width, height, libtcod.BKGND_NONE, libtcod.LEFT, header)

	y = header_height
	letter_index = ord('a')
	for option_text in options:
		text = chr(letter_index)+' - '+option_text
		libtcod.console_print_ex(window, 0, y, libtcod.BKGND_NONE, libtcod.LEFT, text)
		y += 1
		letter_index += 1

	x = SCREEN_WIDTH/2 - width/2
	y = SCREEN_HEIGHT/2 - height/2
	libtcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 0.7)

	libtcod.console_flush()
	key = libtcod.Key()
	libtcod.sys_wait_for_event(libtcod.EVENT_KEY_PRESS, key, mouse, True)

	index = key.c - ord('a')
	if index >= 0 and index < len(options): return index
	return None

def inventory_menu(header):
	if len(inventory) == 0:
		message('No items')
		return None

	options = [item.name for item in inventory]

	index = menu(header, options, INVENTORY_WIDTH)

	if index is None:
		return None
	return inventory[index]

def handle_keys():
	global playerx, playery
	global fov_recompute
	global key

	#key = libtcod.console_check_for_keypress(libtcod.KEY_PRESSED)

	if key.vk == libtcod.KEY_ENTER and key.lalt:  #Toggle fullscreen on alt-enter
		libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
	elif key.vk == libtcod.KEY_ESCAPE:
		return 'exit'

	if key.vk == libtcod.KEY_CHAR:
		if game_state == 'playing':
			fov_recompute = True  #To avoid duplicate code
			if key.c == ord('h'):
				player_move_or_attack(-1, 0)
			elif key.c == ord('j'):
				player_move_or_attack(0, 1)
			elif key.c == ord('k'):
				player_move_or_attack(0, -1)
			elif key.c == ord('l'):
				player_move_or_attack(1, 0)
			elif key.c == ord('y'):
				player_move_or_attack(-1, -1)
			elif key.c == ord('u'):
				player_move_or_attack(1, -1)
			elif key.c == ord('b'):
				player_move_or_attack(-1, 1)
			elif key.c == ord('n'):
				player_move_or_attack(1, 1)
			elif key.c == ord('.'):
				pass #wait a turn
			elif key.c == ord(','):
				for object in objects:  #pick up the first item under the player
					if object.x == player.x and object.y == player.y and object.item:
						object.item.pick_up()
						break
				else:
					message('Nothing to pick up here', libtcod.green)
			elif key.c == ord('i'):
				inventory_menu('Inventory')
				return 'didnt-take-turn'
			elif key.c == ord('d'):
				object = inventory_menu('Drop what?')
				if object is not None:
					object.item.drop()
				else:
					return 'didnt-take-turn'
			elif key.c == ord('e'):
				object = inventory_menu('Use what?')
				if object is not None:
					object.item.use()
			else:
				fov_recompute = False

			if fov_recompute:
				return ''

	return 'didnt-take-turn'

#Graphics init
libtcod.console_set_custom_font('dejavu10x10_gs_tc.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'python/lobtcod tutorial', False)
con = libtcod.console_new(MAP_WIDTH, MAP_HEIGHT)
libtcod.sys_set_fps(LIMIT_FPS)

#UI init
panel = libtcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)
game_msgs = []

#Object init
fighter_component = Fighter(hp=30, defense=2, power=5, death_function=player_death)
player = Object(SCREEN_WIDTH/2, SCREEN_HEIGHT/2, '@', 'player', libtcod.darkest_gray, blocks=True, fighter=fighter_component)
#npc = Object(SCREEN_WIDTH/2, SCREEN_HEIGHT/2 +5, '@', libtcod.white)
objects = [player]

#Inventory init
inventory = []

#Map init
make_map()

#Fov init
fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
for y in range(MAP_HEIGHT):
	for x in range(MAP_WIDTH):
		libtcod.map_set_properties(fov_map, x, y, not map[x][y].opaque, not map[x][y].blocked)
fov_recompute = True

#Pathfinding init
#path_map = libtcod.path_new_using_map(fov_map, 1)

#State init
game_state = 'playing'
player_action= None

#Input init
mouse = libtcod.Mouse()
key = libtcod.Key()

message('Welcome stranger! Prepare to perish in the Halls of the Ancients.', libtcod.red)

while not libtcod.console_is_window_closed():

	libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS|libtcod.EVENT_MOUSE, key, mouse)

	render_all()
	libtcod.console_flush()

	for object in objects:
		object.clear()

	#handle keys and/or exit
	player_action = handle_keys()
	if player_action == 'exit':
		break

	#ai
	if game_state == 'playing' and player_action != 'didnt-take-turn':
		for object in objects:
			if object.ai:
				object.ai.take_turn()