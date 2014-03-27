import libtcodpy as libtcod

SCREEN_WIDTH	= 80
SCREEN_HEIGHT	= 50
MAP_WIDTH		= 80
MAP_HEIGHT		= 45
LIMIT_FPS		= 20
ROOM_MAX_SIZE	= 10
ROOM_MIN_SIZE	= 6
MAX_ROOMS		= 30

color_dark_wall = libtcod.Color(0, 0, 100)
color_dark_ground = libtcod.Color(50, 50, 150)

class Object:  #generic object
	def __init__(self, x, y, char, color):
		self.x = x
		self.y = y
		self.char = char
		self.color = color

	def move(self, dx, dy):  #move by a given amount
		if not map[self.x + dx][self.y + dy].blocked:
			self.x += dx
			self.y += dy

	def draw(self):  #draw the object
		libtcod.console_set_default_foreground(con, self.color)
		libtcod.console_put_char(con, self.x, self.y, self.char, libtcod.BKGND_NONE)

	def clear(self):  #clear yourself
		libtcod.console_put_char(con, self.x, self.y, ' ', libtcod.BKGND_NONE)

class Tile: #a tile on the map
	def __init__(self, blocked, opaque = None):
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
			(new_x, new_y) = new_room.center()

			room_no = Object(new_x, new_y, chr(65+num_rooms), libtcod.white)
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

	for y in range(MAP_HEIGHT):
		for x in range(MAP_WIDTH):
			wall = map[x][y].opaque
			if wall:
				libtcod.console_set_char_background(con, x, y, color_dark_wall, libtcod.BKGND_SET)
			else:
				libtcod.console_set_char_background(con, x, y, color_dark_ground, libtcod.BKGND_SET)

	for object in objects:
		object.draw()

	libtcod.console_blit(con, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)

def handle_keys():
	global playerx, playery

	key = libtcod.console_check_for_keypress(libtcod.KEY_PRESSED)

	if key.vk == libtcod.KEY_CHAR:
		if key.c == ord('h'):
			player.move(-1, 0)
		elif key.c == ord('j'):
			player.move(0, 1)
		elif key.c == ord('k'):
			player.move(0, -1)
		elif key.c == ord('l'):
			player.move(1, 0)
		elif key.c == ord('y'):
			player.move(-1, -1)
		elif key.c == ord('u'):
			player.move(1, -1)
		elif key.c == ord('b'):
			player.move(-1, 1)
		elif key.c == ord('n'):
			player.move(1, 1)

	if key.vk == libtcod.KEY_ENTER and key.lalt:  #Toggle fullscreen on alt-enter
		libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
	elif key.vk == libtcod.KEY_ESCAPE:
		return True

#Graphics init
libtcod.console_set_custom_font('dejavu10x10_gs_tc.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'python/lobtcod tutorial', False)
con = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)
libtcod.sys_set_fps(LIMIT_FPS)

#Object init
player = Object(SCREEN_WIDTH/2, SCREEN_HEIGHT/2, '@', libtcod.green)
npc = Object(SCREEN_WIDTH/2, SCREEN_HEIGHT/2 +5, '@', libtcod.white)
objects = [npc, player]

#Map init
make_map()

while not libtcod.console_is_window_closed():

	render_all()
	libtcod.console_flush()

	for object in objects:
		object.clear()

	#handle keys and/or exit
	exit = handle_keys()
	if exit:
		break