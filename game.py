import libtcodpy as libtcod

SCREEN_WIDTH	= 80
SCREEN_HEIGHT	= 50
MAP_WIDTH		= 80
MAP_HEIGHT		= 45
LIMIT_FPS		= 20

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

def make_map():
	global map

	map = [[ Tile(False)
		for y in range(MAP_HEIGHT) ]
			for x in range(MAP_WIDTH) ]

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
map[30][22].blocked = True
map[30][22].opaque = True
map[50][22].blocked = True
map[50][22].opaque = True

while not libtcod.console_is_window_closed():

	render_all()
	libtcod.console_flush()

	for object in objects:
		object.clear()

	#handle keys and/or exit
	exit = handle_keys()
	if exit:
		break