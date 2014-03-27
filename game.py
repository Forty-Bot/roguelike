import libtcodpy as libtcod

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

MAX_ROOM_MONSTERS = 3

color_dark_wall = libtcod.Color(0, 0, 100)
#color_light_wall = libtcod.Color(130, 110, 50)
color_light_wall = color_dark_wall + libtcod.dark_gray
color_dark_ground = libtcod.Color(50, 50, 150)
#color_light_ground = libtcod.Color(200, 180, 50)
color_light_ground = color_dark_ground + libtcod.dark_grey

class Object:  #generic object
	def __init__(self, x, y, char, name, color, blocks=False):
		self.x = x
		self.y = y
		self.char = char
		self.name = name
		self.color = color
		self.blocks = blocks

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

			room_no = Object(new_x, new_y, chr(65+num_rooms), 'room number', libtcod.white)
			objects.insert(0, room_no)

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
		object.draw()

	libtcod.console_blit(con, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)

def place_objects(room):
	num_monsters = 0
	if libtcod.random_get_int(0, 0, 1) == 1:
		num_monsters = libtcod.random_get_int(0, 0, 3)

	for i in range(0, num_monsters):
		x = libtcod.random_get_int(0, room.x1, room.x2)
		y = libtcod.random_get_int(0, room.y1, room.y2)

		monster_type = libtcod.random_get_int(0, 1, 100)

		if monster_type < 50:
			monster = Object(x, y, 'd', 'dingo', libtcod.desaturated_amber, blocks=True)
		else:
			monster = Object(x, y, 'o', 'orc', libtcod.desaturated_green, blocks=True)

		if not is_blocked(x, y):
			objects.append(monster)

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
		if object.x == x and object.y == y:
			target = object
			break

	if target is not None:
		print 'The '+target.name+' is unharmed.'
	else:
		player.move(dx, dy)
		fov_recompute = True

def handle_keys():
	global playerx, playery
	global fov_recompute

	key = libtcod.console_check_for_keypress(libtcod.KEY_PRESSED)

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
			else:
				fov_recompute = False

			if fov_recompute:
				return ''

	return 'didnt-take-turn'

#Graphics init
libtcod.console_set_custom_font('dejavu10x10_gs_tc.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'python/lobtcod tutorial', False)
con = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)
libtcod.sys_set_fps(LIMIT_FPS)

#Object init
player = Object(SCREEN_WIDTH/2, SCREEN_HEIGHT/2, '@', 'player', libtcod.darkest_gray, blocks=True)
#npc = Object(SCREEN_WIDTH/2, SCREEN_HEIGHT/2 +5, '@', libtcod.white)
objects = [player]

#Map init
make_map()

#Fov init
fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
for y in range(MAP_HEIGHT):
	for x in range(MAP_WIDTH):
		libtcod.map_set_properties(fov_map, x, y, not map[x][y].opaque, not map[x][y].blocked)
fov_recompute = True

#State init
game_state = 'playing'
player_action= None

while not libtcod.console_is_window_closed():

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
			print 'The '+object.name+' growls!'