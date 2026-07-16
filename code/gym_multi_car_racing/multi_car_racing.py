import sys, math
from pathlib import Path
import numpy as np

import Box2D
from Box2D.b2 import (edgeShape, circleShape, fixtureDef, polygonShape, revoluteJointDef, contactListener)

import gym
import gym.envs.box2d.car_dynamics as car_dynamics
from gym import spaces
from gym.utils import colorize, seeding, EzPickle

import pyglet
from pyglet import gl
from shapely.geometry import Point, Polygon

# Easiest continuous control task to learn from pixels, a top-down racing environment.
# Discrete control is reasonable in this environment as well, on/off discretization is
# fine.
#
# State consists of STATE_W x STATE_H pixels.
#
# Reward is -0.1 every frame and +1000/N for every track tile visited, where N is
# the total number of tiles visited in the track. For example, if you have finished in 732 frames,
# your reward is 1000 - 0.1*732 = 926.8 points.
#
# Game is solved when agent consistently gets 900+ points. Track generated is random every episode.
#
# Episode finishes when all tiles are visited. Car also can go outside of PLAYFIELD, that
# is far off the track, then it will get -100 and die.
#
# Some indicators shown at the bottom of the window and the state RGB buffer. From
# left to right: true speed, four ABS sensors, steering wheel position and gyroscope.
#
# To play yourself (it's rather fast for humans), type:
#
# python gym/envs/box2d/car_racing.py
#
# Remember it's powerful rear-wheel drive car, don't press accelerator and turn at the
# same time.
#
# Created by Oleg Klimov. Licensed on the same terms as the rest of OpenAI Gym.

STATE_W = 96   # less than Atari 160x192
STATE_H = 96
VIDEO_W = 600
VIDEO_H = 400
WINDOW_W = 1000
WINDOW_H = 800

SCALE       = 6.0        # Track scale
TRACK_RAD   = 900/SCALE  # Track is heavily morphed circle with this radius
PLAYFIELD   = 2000/SCALE # Game over boundary
FPS         = 50         # Frames per second
ZOOM        = 2.7        # Camera zoom
ZOOM_FOLLOW = True       # Set to False for fixed view (don't use zoom)


TRACK_DETAIL_STEP = 21/SCALE
TRACK_TURN_RATE = 0.31
TRACK_WIDTH = 40/SCALE
BORDER = 8/SCALE
BORDER_MIN_COUNT = 4

ROAD_COLOR = [0.4, 0.4, 0.4]

TELEMETRY_EGO_FEATURES = [
    "ego_x",
    "ego_y",
    "ego_vx",
    "ego_vy",
    "ego_speed",
    "ego_heading_sin",
    "ego_heading_cos",
    "ego_angular_velocity",
    "track_progress",
    "tile_progress",
    "centerline_dx",
    "centerline_dy",
    "lateral_error",
    "heading_error_sin",
    "heading_error_cos",
    "on_grass",
    "driving_backward",
]

TELEMETRY_OPPONENT_FEATURES = [
    "rel_forward",
    "rel_left",
    "rel_vx",
    "rel_vy",
    "distance",
    "heading_error_sin",
    "heading_error_cos",
]

TELEMETRY_DYNAMIC_MASK_FEATURES = [
    "neighbor_mask",
]

DEFAULT_DYNAMIC_MAX_NEIGHBORS = None

# Low-saturation vehicle palette shared with manuscript figures.
CAR_COLORS = [
    (0.137, 0.353, 0.624),
    (0.812, 0.541, 0.525),
    (0.843, 0.647, 0.455),
    (0.804, 0.733, 0.478),
    (0.549, 0.749, 0.608),
    (0.525, 0.722, 0.737),
    (0.616, 0.718, 0.820),
    (0.686, 0.651, 0.812),
    (0.761, 0.635, 0.808),
    (0.420, 0.447, 0.502),
    (0.612, 0.639, 0.686),
    (0.294, 0.333, 0.388),
]

# Distance between cars
LINE_SPACING = 5     # Starting distance between each pair of cars
LATERAL_SPACING = 3  # Starting side distance between pairs of cars

# Penalizing backwards driving
BACKWARD_THRESHOLD = np.pi/2
K_BACKWARD = 0  # Penalty weight: backwards_penalty = K_BACKWARD * angle_diff  (if angle_diff > BACKWARD_THRESHOLD)

class FrictionDetector(contactListener):
    def __init__(self, env):
        contactListener.__init__(self)
        self.env = env
    def BeginContact(self, contact):
        self._contact(contact, True)
    def EndContact(self, contact):
        self._contact(contact, False)
    def _contact(self, contact, begin):
        tile = None
        obj = None
        u1 = contact.fixtureA.body.userData
        u2 = contact.fixtureB.body.userData
        if u1 and "road_friction" in u1.__dict__:
            tile = u1
            obj  = u2
        if u2 and "road_friction" in u2.__dict__:
            tile = u2
            obj  = u1
        if not tile:
            return

        tile.color[0] = ROAD_COLOR[0]
        tile.color[1] = ROAD_COLOR[1]
        tile.color[2] = ROAD_COLOR[2]

        # This check seems to implicitly make sure that we only look at wheels as the tiles 
        # attribute is only set for wheels in car_dynamics.py.
        if not obj or "tiles" not in obj.__dict__:
            return
        if begin:
            obj.tiles.add(tile)
            # print tile.road_friction, "ADD", len(obj.tiles)
            if not tile.road_visited[obj.car_id]:
                tile.road_visited[obj.car_id] = True
                self.env.tile_visited_count[obj.car_id] += 1

                # The reward is dampened on tiles that have been visited already.
                past_visitors = sum(tile.road_visited)-1
                reward_factor = 1 - (past_visitors / self.env.num_agents)
                self.env.reward[obj.car_id] += reward_factor * 1000.0/len(self.env.track)
        else:
            obj.tiles.remove(tile)
            # print tile.road_friction, "DEL", len(obj.tiles) -- should delete to zero when on grass (this works)

class MultiCarRacing(gym.Env, EzPickle):
    metadata = {
        'render.modes': ['human', 'rgb_array', 'state_pixels'],
        'video.frames_per_second' : FPS
    }

    def __init__(self, num_agents=2, verbose=1, direction='CCW',
                 use_random_direction=True, backwards_flag=True, h_ratio=0.25,
                 use_ego_color=False, observation_type='pixels',
                 start_order=None, line_spacing=LINE_SPACING,
                 lateral_spacing=LATERAL_SPACING, track_path=None,
                 max_neighbors=DEFAULT_DYNAMIC_MAX_NEIGHBORS):
        EzPickle.__init__(self)
        if observation_type not in ['pixels', 'telemetry', 'telemetry_dynamic']:
            raise ValueError("observation_type must be 'pixels', 'telemetry', or 'telemetry_dynamic'")
        self.seed()
        self.num_agents = num_agents
        self.observation_type = observation_type
        self.contactListener_keepref = FrictionDetector(self)
        self.world = Box2D.b2World((0,0), contactListener=self.contactListener_keepref)
        self.viewer = [None] * num_agents
        self.invisible_state_window = None
        self.invisible_video_window = None
        self.road = None
        self.cars = [None] * num_agents
        self.car_order = None  # Determines starting positions of cars
        self.reward = np.zeros(num_agents)
        self.prev_reward = np.zeros(num_agents)
        self.tile_visited_count = [0]*num_agents
        self.verbose = verbose
        self.fd_tile = fixtureDef(
                shape = polygonShape(vertices=
                    [(0, 0),(1, 0),(1, -1),(0, -1)]))
        self.driving_backward = np.zeros(num_agents, dtype=bool)
        self.driving_on_grass = np.zeros(num_agents, dtype=bool)
        self.use_random_direction = use_random_direction  # Whether to select direction randomly
        self.episode_direction = direction  # Choose 'CCW' (default) or 'CW' (flipped)
        if self.use_random_direction:  # Choose direction randomly
            self.episode_direction = np.random.choice(['CW', 'CCW'])
        self.backwards_flag = backwards_flag  # Boolean for rendering backwards driving flag
        self.h_ratio = h_ratio  # Configures vertical location of car within rendered window
        self.use_ego_color = use_ego_color  # Whether to make ego car always render as the same color
        self.start_order = list(start_order) if start_order is not None else None
        self.line_spacing = line_spacing
        self.lateral_spacing = lateral_spacing
        self.track_path = str(track_path) if track_path is not None else None
        if max_neighbors is None or int(max_neighbors) <= 0:
            self.max_neighbors = max(self.num_agents - 1, 0)
            self.max_neighbors_unbounded = True
        else:
            self.max_neighbors = int(max_neighbors)
            self.max_neighbors_unbounded = False
        self.last_dynamic_neighbor_ids = [[] for _ in range(self.num_agents)]

        self.action_lb = np.tile(np.array([-1,+0,+0]), (self.num_agents, 1))
        self.action_ub = np.tile(np.array([+1,+1,+1]), (self.num_agents, 1))

        self.action_space = spaces.Box( self.action_lb, self.action_ub, dtype=np.float32)  # (steer, gas, brake) x N
        if self.observation_type == 'pixels':
            self.observation_space = spaces.Box(
                low=0, high=255,
                shape=(self.num_agents, STATE_H, STATE_W, 3),
                dtype=np.uint8)
        else:
            self.observation_space = spaces.Box(
                low=-np.inf,
                high=np.inf,
                shape=(self.num_agents, self.telemetry_feature_dim),
                dtype=np.float32,
            )

    @property
    def telemetry_feature_dim(self):
        if self.observation_type == 'telemetry_dynamic':
            return len(TELEMETRY_EGO_FEATURES) + \
                self.max_neighbors * (len(TELEMETRY_OPPONENT_FEATURES) + 1)
        return len(TELEMETRY_EGO_FEATURES) + \
            (self.num_agents - 1) * len(TELEMETRY_OPPONENT_FEATURES)

    @property
    def telemetry_feature_names(self):
        names = list(TELEMETRY_EGO_FEATURES)
        if self.observation_type == 'telemetry_dynamic':
            for opponent_slot in range(self.max_neighbors):
                names.extend([
                    f"opponent_{opponent_slot}_{name}"
                    for name in TELEMETRY_OPPONENT_FEATURES
                ])
                names.append(f"opponent_{opponent_slot}_neighbor_mask")
        else:
            for opponent_slot in range(self.num_agents - 1):
                names.extend([
                    f"opponent_{opponent_slot}_{name}"
                    for name in TELEMETRY_OPPONENT_FEATURES
                ])
        return names


    def seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        return [seed]

    def _create_track_from_file(self):
        data = np.load(self.track_path, allow_pickle=True)
        center = np.asarray(data["center"], dtype=np.float32)
        if center.ndim != 2 or center.shape[1] != 2 or len(center) < 8:
            raise ValueError(f"invalid custom track centerline in {self.track_path}")
        if "left" in data and "right" in data:
            left = np.asarray(data["left"], dtype=np.float32)
            right = np.asarray(data["right"], dtype=np.float32)
        else:
            left = None
            right = None
        use_file_borders = bool(data["use_file_borders"]) if "use_file_borders" in data else False

        self.road = []
        track = []
        n = len(center)
        for i in range(n):
            prev_point = center[(i - 1) % n]
            next_point = center[(i + 1) % n]
            tangent = next_point - prev_point
            if float(np.linalg.norm(tangent)) < 1e-6:
                tangent = center[i] - center[(i - 1) % n]
            tangent_angle = math.atan2(float(tangent[1]), float(tangent[0]))
            beta = tangent_angle - math.pi / 2.0
            track.append((2 * math.pi * i / n, beta, float(center[i, 0]), float(center[i, 1])))

        border = [False] * n
        for i in range(n):
            _, beta1, x1, y1 = track[i]
            _, beta2, x2, y2 = track[i - 1]
            if use_file_borders and left is not None and right is not None:
                road1_l = tuple(map(float, left[i]))
                road1_r = tuple(map(float, right[i]))
                road2_l = tuple(map(float, left[i - 1]))
                road2_r = tuple(map(float, right[i - 1]))
            else:
                road1_l = (x1 - TRACK_WIDTH * math.cos(beta1), y1 - TRACK_WIDTH * math.sin(beta1))
                road1_r = (x1 + TRACK_WIDTH * math.cos(beta1), y1 + TRACK_WIDTH * math.sin(beta1))
                road2_l = (x2 - TRACK_WIDTH * math.cos(beta2), y2 - TRACK_WIDTH * math.sin(beta2))
                road2_r = (x2 + TRACK_WIDTH * math.cos(beta2), y2 + TRACK_WIDTH * math.sin(beta2))
            vertices = [road1_l, road1_r, road2_r, road2_l]
            self.fd_tile.shape.vertices = vertices
            t = self.world.CreateStaticBody(fixtures=self.fd_tile)
            t.userData = t
            c = 0.01 * (i % 3)
            t.color = [ROAD_COLOR[0] + c, ROAD_COLOR[1] + c, ROAD_COLOR[2] + c]
            t.road_visited = [False] * self.num_agents
            t.road_friction = 1.0
            t.fixtures[0].sensor = True
            self.road_poly.append((vertices, t.color))
            self.road.append(t)

        self.track = track
        self.road_poly_shapely = [Polygon(self.road_poly[i][0]) for i in range(len(self.road_poly))]
        if self.verbose == 1:
            print(f"Loaded custom track: {Path(self.track_path).name} -> {len(track)}-tiles track")
        return True

    def _destroy(self):
        if not self.road:
            return
        for t in self.road:
            self.world.DestroyBody(t)
        self.road = []

        for car in self.cars:
            car.destroy()

    def _create_track(self):
        CHECKPOINTS = 12

        # Create checkpoints
        checkpoints = []
        for c in range(CHECKPOINTS):
            alpha = 2*math.pi*c/CHECKPOINTS + self.np_random.uniform(0, 2*math.pi*1/CHECKPOINTS)
            rad = self.np_random.uniform(TRACK_RAD/3, TRACK_RAD)
            if c==0:
                alpha = 0
                rad = 1.5*TRACK_RAD
            if c==CHECKPOINTS-1:
                alpha = 2*math.pi*c/CHECKPOINTS
                self.start_alpha = 2*math.pi*(-0.5)/CHECKPOINTS
                rad = 1.5*TRACK_RAD
            checkpoints.append( (alpha, rad*math.cos(alpha), rad*math.sin(alpha)) )

        # print "\n".join(str(h) for h in checkpoints)
        # self.road_poly = [ (    # uncomment this to see checkpoints
        #    [ (tx,ty) for a,tx,ty in checkpoints ],
        #    (0.7,0.7,0.9) ) ]
        self.road = []

        # Go from one checkpoint to another to create track
        x, y, beta = 1.5*TRACK_RAD, 0, 0
        dest_i = 0
        laps = 0
        track = []
        no_freeze = 2500
        visited_other_side = False
        while True:
            alpha = math.atan2(y, x)
            if visited_other_side and alpha > 0:
                laps += 1
                visited_other_side = False
            if alpha < 0:
                visited_other_side = True
                alpha += 2*math.pi
            while True: # Find destination from checkpoints
                failed = True
                while True:
                    dest_alpha, dest_x, dest_y = checkpoints[dest_i % len(checkpoints)]
                    if alpha <= dest_alpha:
                        failed = False
                        break
                    dest_i += 1
                    if dest_i % len(checkpoints) == 0:
                        break
                if not failed:
                    break
                alpha -= 2*math.pi
                continue
            r1x = math.cos(beta)
            r1y = math.sin(beta)
            p1x = -r1y
            p1y = r1x
            dest_dx = dest_x - x  # vector towards destination
            dest_dy = dest_y - y
            proj = r1x*dest_dx + r1y*dest_dy  # destination vector projected on rad
            while beta - alpha >  1.5*math.pi:
                 beta -= 2*math.pi
            while beta - alpha < -1.5*math.pi:
                 beta += 2*math.pi
            prev_beta = beta
            proj *= SCALE
            if proj >  0.3:
                 beta -= min(TRACK_TURN_RATE, abs(0.001*proj))
            if proj < -0.3:
                 beta += min(TRACK_TURN_RATE, abs(0.001*proj))
            x += p1x*TRACK_DETAIL_STEP
            y += p1y*TRACK_DETAIL_STEP
            track.append( (alpha,prev_beta*0.5 + beta*0.5,x,y) )
            if laps > 4:
                 break
            no_freeze -= 1
            if no_freeze==0:
                 break
        # print "\n".join([str(t) for t in enumerate(track)])

        # Find closed loop range i1..i2, first loop should be ignored, second is OK
        i1, i2 = -1, -1
        i = len(track)
        while True:
            i -= 1
            if i==0:
                return False  # Failed
            pass_through_start = track[i][0] > self.start_alpha \
                and track[i-1][0] <= self.start_alpha
            if pass_through_start and i2==-1:
                i2 = i
            elif pass_through_start and i1==-1:
                i1 = i
                break
        if self.verbose == 1:
            print("Track generation: %i..%i -> %i-tiles track" % (i1, i2, i2-i1))
        assert i1!=-1
        assert i2!=-1

        track = track[i1:i2-1]

        first_beta = track[0][1]
        first_perp_x = math.cos(first_beta)
        first_perp_y = math.sin(first_beta)
        # Length of perpendicular jump to put together head and tail
        well_glued_together = np.sqrt(
            np.square( first_perp_x*(track[0][2] - track[-1][2]) ) +
            np.square( first_perp_y*(track[0][3] - track[-1][3]) ))
        if well_glued_together > TRACK_DETAIL_STEP:
            return False

        # Red-white border on hard turns
        border = [False]*len(track)
        for i in range(len(track)):
            good = True
            oneside = 0
            for neg in range(BORDER_MIN_COUNT):
                beta1 = track[i-neg-0][1]
                beta2 = track[i-neg-1][1]
                good &= abs(beta1 - beta2) > TRACK_TURN_RATE*0.2
                oneside += np.sign(beta1 - beta2)
            good &= abs(oneside) == BORDER_MIN_COUNT
            border[i] = good
        for i in range(len(track)):
            for neg in range(BORDER_MIN_COUNT):
                border[i-neg] |= border[i]

        # Create tiles
        for i in range(len(track)):
            _, beta1, x1, y1 = track[i]
            _, beta2, x2, y2 = track[i-1]
            road1_l = (x1 - TRACK_WIDTH*math.cos(beta1), y1 - TRACK_WIDTH*math.sin(beta1))
            road1_r = (x1 + TRACK_WIDTH*math.cos(beta1), y1 + TRACK_WIDTH*math.sin(beta1))
            road2_l = (x2 - TRACK_WIDTH*math.cos(beta2), y2 - TRACK_WIDTH*math.sin(beta2))
            road2_r = (x2 + TRACK_WIDTH*math.cos(beta2), y2 + TRACK_WIDTH*math.sin(beta2))
            vertices = [road1_l, road1_r, road2_r, road2_l]
            self.fd_tile.shape.vertices = vertices
            t = self.world.CreateStaticBody(fixtures=self.fd_tile)
            t.userData = t
            c = 0.01*(i%3)
            t.color = [ROAD_COLOR[0] + c, ROAD_COLOR[1] + c, ROAD_COLOR[2] + c]
            t.road_visited = [False]*self.num_agents
            t.road_friction = 1.0
            t.fixtures[0].sensor = True
            self.road_poly.append(( [road1_l, road1_r, road2_r, road2_l], t.color ))
            self.road.append(t)
            if border[i]:
                side = np.sign(beta2 - beta1)
                b1_l = (x1 + side* TRACK_WIDTH        *math.cos(beta1), y1 + side* TRACK_WIDTH        *math.sin(beta1))
                b1_r = (x1 + side*(TRACK_WIDTH+BORDER)*math.cos(beta1), y1 + side*(TRACK_WIDTH+BORDER)*math.sin(beta1))
                b2_l = (x2 + side* TRACK_WIDTH        *math.cos(beta2), y2 + side* TRACK_WIDTH        *math.sin(beta2))
                b2_r = (x2 + side*(TRACK_WIDTH+BORDER)*math.cos(beta2), y2 + side*(TRACK_WIDTH+BORDER)*math.sin(beta2))
                self.road_poly.append(( [b1_l, b1_r, b2_r, b2_l], (1,1,1) if i%2==0 else (1,0,0) ))
        self.track = track
        self.road_poly_shapely = [Polygon(self.road_poly[i][0]) for i in
                                  range(len(self.road_poly))]
        return True

    def reset(self):
        self._destroy()
        self.reward = np.zeros(self.num_agents)
        self.prev_reward = np.zeros(self.num_agents)
        self.tile_visited_count = [0]*self.num_agents
        self.t = 0.0
        self.road_poly = []

        # Reset driving backwards/on-grass states and track direction
        self.driving_backward = np.zeros(self.num_agents, dtype=bool)
        self.driving_on_grass = np.zeros(self.num_agents, dtype=bool)
        if self.use_random_direction:  # Choose direction randomly
            self.episode_direction = np.random.choice(['CW', 'CCW'])

        # Set positions of cars randomly
        ids = [i for i in range(self.num_agents)]
        if self.start_order is None:
            shuffle_ids = np.random.choice(ids, size=self.num_agents, replace=False)
        else:
            if len(self.start_order) != self.num_agents:
                raise ValueError("start_order must provide one starting slot per agent")
            if len(set(self.start_order)) != self.num_agents or min(self.start_order) < 0:
                raise ValueError("start_order slots must be unique non-negative integers")
            shuffle_ids = np.asarray(self.start_order, dtype=np.int32)
        self.car_order = {i: int(shuffle_ids[i]) for i in range(self.num_agents)}

        if self.track_path is not None:
            success = self._create_track_from_file()
            if not success:
                raise RuntimeError(f"failed to load custom track from {self.track_path}")
        else:
            while True:
                success = self._create_track()
                if success:
                    break
                if self.verbose == 1:
                    print("retry to generate track (normal if there are not many of this messages)")

        (angle, pos_x, pos_y) = self.track[0][1:4]
        car_width = car_dynamics.SIZE * (car_dynamics.WHEEL_W * 2 \
            + (car_dynamics.WHEELPOS[1][0]-car_dynamics.WHEELPOS[1][0]))
        for car_id in range(self.num_agents):

            # Specify line and lateral separation between cars
            line_spacing = self.line_spacing
            lateral_spacing = self.lateral_spacing

            #index into positions using modulo and pairs
            line_number = math.floor(self.car_order[car_id] / 2)  # Starts at 0
            side = (2 * (self.car_order[car_id] % 2)) - 1  # either {-1, 1}

            # Compute offsets from start (this should be zero for first pair of cars)
            dx = self.track[-line_number * line_spacing][2] - pos_x  # x offset
            dy = self.track[-line_number * line_spacing][3] - pos_y  # y offset

            # Compute angle based off of track index for car
            angle = self.track[-line_number * line_spacing][1]
            if self.episode_direction == 'CW':  # CW direction indicates reversed
                angle -= np.pi  # Flip direction is either 0 or pi

            # Compute offset angle (normal to angle of track)
            norm_theta = angle - np.pi/2

            # Compute offsets from position of original starting line
            new_x = pos_x + dx + (lateral_spacing * np.sin(norm_theta) * side)
            new_y = pos_y + dy + (lateral_spacing * np.cos(norm_theta) * side)

            # Display spawn locations of cars.
            # print(f"Spawning car {car_id} at {new_x:.0f}x{new_y:.0f} with "
            #       f"orientation {angle}")

            # Create car at location with given angle
            self.cars[car_id] = car_dynamics.Car(self.world, angle, new_x,
                                                 new_y)
            self.cars[car_id].hull.color = CAR_COLORS[car_id % len(CAR_COLORS)]

            # This will be used to identify the car that touches a particular tile.
            for wheel in self.cars[car_id].wheels:
                wheel.car_id = car_id

        return self.step(None)[0]

    def step(self, action):
        """ Run environment for one timestep. 
        
        Parameters:
            action(np.ndarray): Numpy array of shape (num_agents,3) containing the
                commands for each car. Each command is of the shape (steer, gas, brake).
        """

        if action is not None:
            # NOTE: re-shape action as input action is flattened
            action = np.reshape(action, (self.num_agents, -1))
            for car_id, car in enumerate(self.cars):
                car.steer(-action[car_id][0])
                car.gas(action[car_id][1])
                car.brake(action[car_id][2])

        for car in self.cars:
            car.step(1.0/FPS)
        self.world.Step(1.0/FPS, 6*30, 2*30)
        self.t += 1.0/FPS

        step_reward = np.zeros(self.num_agents)
        done = False
        if action is not None: # First step without action, called from reset()
            self.reward -= 0.1
            # We actually don't want to count fuel spent, we want car to be faster.
            # self.reward -=  10 * self.car.fuel_spent / ENGINE_POWER

            # NOTE(IG): Probably not relevant. Seems not to be used anywhere. Commented it out.
            # self.cars[0].fuel_spent = 0.0

            step_reward = self.reward - self.prev_reward

            # Add penalty for driving backward
            for car_id, car in enumerate(self.cars):  # Enumerate through cars

                # Get car speed
                vel = car.hull.linearVelocity
                if np.linalg.norm(vel) > 0.5:  # If fast, compute angle with v
                    car_angle = -math.atan2(vel[0], vel[1])
                else:  # If slow, compute with hull
                    car_angle = car.hull.angle

                # Map angle to [0, 2pi] interval
                car_angle = (car_angle + (2 * np.pi)) % (2 * np.pi)

                # Retrieve car position
                car_pos = np.array(car.hull.position).reshape((1, 2))
                car_pos_as_point = Point((float(car_pos[:, 0]),
                                          float(car_pos[:, 1])))


                # Compute closest point on track to car position (l2 norm)
                distance_to_tiles = np.linalg.norm(
                    car_pos - np.array(self.track)[:, 2:], ord=2, axis=1)
                track_index = np.argmin(distance_to_tiles)

                # Check if car is driving on grass by checking inside polygons
                on_grass = not np.array([car_pos_as_point.within(polygon)
                                   for polygon in self.road_poly_shapely]).any()
                self.driving_on_grass[car_id] = on_grass

                # Find track angle of closest point
                desired_angle = self.track[track_index][1]

                # If track direction reversed, reverse desired angle
                if self.episode_direction == 'CW':  # CW direction indicates reversed
                    desired_angle += np.pi

                # Map angle to [0, 2pi] interval
                desired_angle = (desired_angle + (2 * np.pi)) % (2 * np.pi)

                # Compute smallest angle difference between desired and car
                angle_diff = abs(desired_angle - car_angle)
                if angle_diff > np.pi:
                    angle_diff = abs(angle_diff - 2 * np.pi)

                # If car is driving backward and not on grass, penalize car. The
                # backwards flag is set even if it is driving on grass.
                if angle_diff > BACKWARD_THRESHOLD:
                    self.driving_backward[car_id] = True
                    step_reward[car_id] -= K_BACKWARD * angle_diff
                else:
                    self.driving_backward[car_id] = False

            self.prev_reward = self.reward.copy()
            if len(self.track) in self.tile_visited_count:
                done = True

            # The car that leaves the field experiences a reward of -100 
            # and the episode is terminated subsequently.
            for car_id, car in enumerate(self.cars):
                x, y = car.hull.position
                if abs(x) > PLAYFIELD or abs(y) > PLAYFIELD:
                    done = True
                    step_reward[car_id] = -100

        if self.observation_type == 'pixels':
            self.state = self.render("state_pixels")
        else:
            if self.observation_type == 'telemetry_dynamic':
                self.state = self._get_telemetry_dynamic_state()
            else:
                self.state = self._get_telemetry_state()

        return self.state, step_reward, done, {}

    def _wrap_to_pi(self, angle):
        return (angle + math.pi) % (2 * math.pi) - math.pi

    def _get_telemetry_state(self):
        """Return normalized privileged state for state-based racing baselines."""
        track_xy = np.array(self.track)[:, 2:]
        state = np.zeros(
            (self.num_agents, self.telemetry_feature_dim),
            dtype=np.float32,
        )

        positions = [np.array(car.hull.position, dtype=np.float32)
                     for car in self.cars]
        velocities = [np.array(car.hull.linearVelocity, dtype=np.float32)
                      for car in self.cars]

        for car_id, car in enumerate(self.cars):
            pos = positions[car_id]
            vel = velocities[car_id]
            heading = float(car.hull.angle)
            heading_vec = np.array([math.cos(heading), math.sin(heading)])
            left_vec = np.array([-math.sin(heading), math.cos(heading)])

            distance_to_track = np.linalg.norm(pos.reshape(1, 2) - track_xy, axis=1)
            track_index = int(np.argmin(distance_to_track))
            _, desired_angle, center_x, center_y = self.track[track_index]
            if self.episode_direction == 'CW':
                desired_angle += math.pi

            center_delta = pos - np.array([center_x, center_y], dtype=np.float32)
            normal = np.array(
                [-math.sin(desired_angle), math.cos(desired_angle)],
                dtype=np.float32,
            )
            heading_error = self._wrap_to_pi(desired_angle - heading)
            speed = float(np.linalg.norm(vel))
            tile_progress = 0.0
            if len(self.track) > 0:
                tile_progress = self.tile_visited_count[car_id] / len(self.track)

            features = [
                pos[0] / PLAYFIELD,
                pos[1] / PLAYFIELD,
                vel[0] / 50.0,
                vel[1] / 50.0,
                speed / 50.0,
                math.sin(heading),
                math.cos(heading),
                float(car.hull.angularVelocity) / 5.0,
                track_index / max(len(self.track) - 1, 1),
                tile_progress,
                center_delta[0] / TRACK_WIDTH,
                center_delta[1] / TRACK_WIDTH,
                float(np.dot(center_delta, normal) / TRACK_WIDTH),
                math.sin(heading_error),
                math.cos(heading_error),
                float(self.driving_on_grass[car_id]),
                float(self.driving_backward[car_id]),
            ]

            for other_id in range(self.num_agents):
                if other_id == car_id:
                    continue

                other = self.cars[other_id]
                rel_pos = positions[other_id] - pos
                rel_vel = velocities[other_id] - vel
                rel_heading = self._wrap_to_pi(float(other.hull.angle) - heading)
                features.extend([
                    float(np.dot(rel_pos, heading_vec) / PLAYFIELD),
                    float(np.dot(rel_pos, left_vec) / PLAYFIELD),
                    rel_vel[0] / 50.0,
                    rel_vel[1] / 50.0,
                    float(np.linalg.norm(rel_pos) / PLAYFIELD),
                    math.sin(rel_heading),
                    math.cos(rel_heading),
                ])

            state[car_id] = np.asarray(features, dtype=np.float32)

        return state

    def _opponent_dynamic_score(self, ego_id, other_id, positions, velocities):
        ego = self.cars[ego_id]
        other = self.cars[other_id]
        ego_pos = positions[ego_id]
        other_pos = positions[other_id]
        ego_vel = velocities[ego_id]
        other_vel = velocities[other_id]
        heading = float(ego.hull.angle)
        heading_vec = np.array([math.cos(heading), math.sin(heading)])
        left_vec = np.array([-math.sin(heading), math.cos(heading)])
        rel_pos = other_pos - ego_pos
        rel_vel = other_vel - ego_vel
        rel_forward = float(np.dot(rel_pos, heading_vec) / PLAYFIELD)
        rel_left = float(np.dot(rel_pos, left_vec) / PLAYFIELD)
        distance = float(np.linalg.norm(rel_pos) / PLAYFIELD)
        closing = float(max(-np.dot(rel_vel, heading_vec) / 50.0, 0.0))
        track_xy = np.array(self.track)[:, 2:]
        ego_idx = int(np.argmin(np.linalg.norm(ego_pos.reshape(1, 2) - track_xy, axis=1)))
        other_idx = int(np.argmin(np.linalg.norm(other_pos.reshape(1, 2) - track_xy, axis=1)))
        track_gap = (other_idx - ego_idx) % max(len(self.track), 1)
        track_gap = min(track_gap, len(self.track) - track_gap) / max(len(self.track), 1)
        return 2.4 * max(rel_forward, 0.0) - 1.1 * abs(rel_left) - 0.35 * distance + 0.30 * closing + 0.15 * (1.0 - track_gap)

    def _get_telemetry_dynamic_state(self):
        """Return a fixed-size dynamic-neighbor telemetry state.

        The ego part matches the standard telemetry state. The opponent part is
        packed from the most relevant nearby vehicles at runtime and padded to a
        fixed max-neighbor budget.
        """
        track_xy = np.array(self.track)[:, 2:]
        state = np.zeros(
            (self.num_agents, self.telemetry_feature_dim),
            dtype=np.float32,
        )
        positions = [np.array(car.hull.position, dtype=np.float32) for car in self.cars]
        velocities = [np.array(car.hull.linearVelocity, dtype=np.float32) for car in self.cars]
        dynamic_neighbor_ids = [[] for _ in range(self.num_agents)]

        for car_id, car in enumerate(self.cars):
            pos = positions[car_id]
            vel = velocities[car_id]
            heading = float(car.hull.angle)
            heading_vec = np.array([math.cos(heading), math.sin(heading)])
            left_vec = np.array([-math.sin(heading), math.cos(heading)])

            distance_to_track = np.linalg.norm(pos.reshape(1, 2) - track_xy, axis=1)
            track_index = int(np.argmin(distance_to_track))
            _, desired_angle, center_x, center_y = self.track[track_index]
            if self.episode_direction == 'CW':
                desired_angle += math.pi

            center_delta = pos - np.array([center_x, center_y], dtype=np.float32)
            normal = np.array([-math.sin(desired_angle), math.cos(desired_angle)], dtype=np.float32)
            heading_error = self._wrap_to_pi(desired_angle - heading)
            speed = float(np.linalg.norm(vel))
            tile_progress = self.tile_visited_count[car_id] / len(self.track) if len(self.track) > 0 else 0.0

            features = [
                pos[0] / PLAYFIELD,
                pos[1] / PLAYFIELD,
                vel[0] / 50.0,
                vel[1] / 50.0,
                speed / 50.0,
                math.sin(heading),
                math.cos(heading),
                float(car.hull.angularVelocity) / 5.0,
                track_index / max(len(self.track) - 1, 1),
                tile_progress,
                center_delta[0] / TRACK_WIDTH,
                center_delta[1] / TRACK_WIDTH,
                float(np.dot(center_delta, normal) / TRACK_WIDTH),
                math.sin(heading_error),
                math.cos(heading_error),
                float(self.driving_on_grass[car_id]),
                float(self.driving_backward[car_id]),
            ]

            candidates = []
            for other_id in range(self.num_agents):
                if other_id == car_id:
                    continue
                other = self.cars[other_id]
                rel_pos = positions[other_id] - pos
                rel_vel = velocities[other_id] - vel
                rel_heading = self._wrap_to_pi(float(other.hull.angle) - heading)
                opp = np.asarray(
                    [
                        float(np.dot(rel_pos, heading_vec) / PLAYFIELD),
                        float(np.dot(rel_pos, left_vec) / PLAYFIELD),
                        rel_vel[0] / 50.0,
                        rel_vel[1] / 50.0,
                        float(np.linalg.norm(rel_pos) / PLAYFIELD),
                        math.sin(rel_heading),
                        math.cos(rel_heading),
                    ],
                    dtype=np.float32,
                )
                score = self._opponent_dynamic_score(car_id, other_id, positions, velocities)
                candidates.append((score, other_id, opp))
            candidates.sort(key=lambda item: item[0], reverse=True)

            for slot in range(self.max_neighbors):
                if slot < len(candidates):
                    opp = candidates[slot][2]
                    dynamic_neighbor_ids[car_id].append(int(candidates[slot][1]))
                    mask = 1.0
                else:
                    opp = np.zeros((len(TELEMETRY_OPPONENT_FEATURES),), dtype=np.float32)
                    mask = 0.0
                features.extend(opp.tolist())
                features.append(mask)

            state[car_id] = np.asarray(features, dtype=np.float32)

        self.last_dynamic_neighbor_ids = dynamic_neighbor_ids
        return state

    def render(self, mode='human'):
        assert mode in ['human', 'state_pixels', 'rgb_array']

        result = []
        for cur_car_id in range(self.num_agents):
            result.append(self._render_window(cur_car_id, mode))
        
        return np.stack(result, axis=0)

    def _render_window(self, car_id, mode):
        """ Performs the actual rendering for each car individually. 
        
        Parameters:
            car_id(int): Numerical id of car for which the corresponding window
                will be rendered.
            mode(str): Rendering mode.
        """

        if self.viewer[car_id] is None:
            from gym.envs.classic_control import rendering
            self.viewer[car_id] = rendering.Viewer(WINDOW_W, WINDOW_H)
            self.viewer[car_id].window.set_caption(f"Car {car_id}")
            self.score_label = pyglet.text.Label('0000', font_size=36,
                x=20, y=WINDOW_H*2.5/40.00, anchor_x='left', anchor_y='center',
                color=(255,255,255,255))
            self.transform = rendering.Transform()

        if "t" not in self.__dict__: return  # reset() not called yet

        zoom = 0.1*SCALE*max(1-self.t, 0) + ZOOM*SCALE*min(self.t, 1)   # Animate zoom first second
        #NOTE (ig): Following two variables seemed unused. Commented them out.
        #zoom_state  = ZOOM*SCALE*STATE_W/WINDOW_W 
        #zoom_video  = ZOOM*SCALE*VIDEO_W/WINDOW_W
        scroll_x = self.cars[car_id].hull.position[0]
        scroll_y = self.cars[car_id].hull.position[1]
        angle = -self.cars[car_id].hull.angle
        vel = self.cars[car_id].hull.linearVelocity
        if np.linalg.norm(vel) > 0.5:
            angle = math.atan2(vel[0], vel[1])
        self.transform.set_scale(zoom, zoom)

        # Positions car in the center with regard to the window width and 1/4 height away from the bottom.
        self.transform.set_translation(
            WINDOW_W/2 - (scroll_x*zoom*math.cos(angle) - scroll_y*zoom*math.sin(angle)),
            WINDOW_H * self.h_ratio - (scroll_x*zoom*math.sin(angle) + scroll_y*zoom*math.cos(angle)) )
        self.transform.set_rotation(angle)

        # Set colors for each viewer and draw cars
        for id, car in enumerate(self.cars):
            if self.use_ego_color:  # Apply same ego car color coloring scheme
                car.hull.color = (0.0, 0.0, 0.8)  # Set all other car colors to blue
                if id == car_id:  # Ego car
                    car.hull.color = (0.8, 0.0, 0.0)  # Set ego car color to red
            car.draw(self.viewer[car_id], mode != "state_pixels")

        arr = None
        win = self.viewer[car_id].window
        win.switch_to()
        win.dispatch_events()

        win.clear()
        t = self.transform
        if mode=='rgb_array':
            VP_W = VIDEO_W
            VP_H = VIDEO_H
        elif mode == 'state_pixels':
            VP_W = STATE_W
            VP_H = STATE_H
        else:
            pixel_scale = 1
            if hasattr(win.context, '_nscontext'):
                pixel_scale = win.context._nscontext.view().backingScaleFactor()  # pylint: disable=protected-access
            VP_W = int(pixel_scale * WINDOW_W)
            VP_H = int(pixel_scale * WINDOW_H)

        gl.glViewport(0, 0, VP_W, VP_H)
        t.enable()
        self.render_road()
        for geom in self.viewer[car_id].onetime_geoms:
           geom.render()
        self.viewer[car_id].onetime_geoms = []
        t.disable()
        self.render_indicators(car_id, WINDOW_W, WINDOW_H)

        if mode == 'human':
            win.flip()
            return self.viewer[car_id].isopen

        image_data = pyglet.image.get_buffer_manager().get_color_buffer().get_image_data()
        arr = np.fromstring(image_data.get_data(), dtype=np.uint8, sep='')
        arr = arr.reshape(VP_H, VP_W, 4)
        arr = arr[::-1, :, 0:3]

        return arr

    def close(self):
        if None not in self.viewer:
            for viewer in self.viewer:
                viewer.close()

        self.viewer = [None] * self.num_agents

    def render_road(self):
        gl.glBegin(gl.GL_QUADS)
        gl.glColor4f(0.4, 0.8, 0.4, 1.0)
        gl.glVertex3f(-PLAYFIELD, +PLAYFIELD, 0)
        gl.glVertex3f(+PLAYFIELD, +PLAYFIELD, 0)
        gl.glVertex3f(+PLAYFIELD, -PLAYFIELD, 0)
        gl.glVertex3f(-PLAYFIELD, -PLAYFIELD, 0)
        gl.glColor4f(0.4, 0.9, 0.4, 1.0)
        k = PLAYFIELD/20.0
        for x in range(-20, 20, 2):
            for y in range(-20, 20, 2):
                gl.glVertex3f(k*x + k, k*y + 0, 0)
                gl.glVertex3f(k*x + 0, k*y + 0, 0)
                gl.glVertex3f(k*x + 0, k*y + k, 0)
                gl.glVertex3f(k*x + k, k*y + k, 0)
        for poly, color in self.road_poly:
            gl.glColor4f(color[0], color[1], color[2], 1)
            for p in poly:
                gl.glVertex3f(p[0], p[1], 0)
        gl.glEnd()

    def render_indicators(self, agent_id, W, H):
        gl.glBegin(gl.GL_QUADS)
        s = W/40.0
        h = H/40.0
        gl.glColor4f(0,0,0,1)
        gl.glVertex3f(W, 0, 0)
        gl.glVertex3f(W, 5*h, 0)
        gl.glVertex3f(0, 5*h, 0)
        gl.glVertex3f(0, 0, 0)
        def vertical_ind(place, val, color):
            gl.glColor4f(color[0], color[1], color[2], 1)
            gl.glVertex3f((place+0)*s, h + h*val, 0)
            gl.glVertex3f((place+1)*s, h + h*val, 0)
            gl.glVertex3f((place+1)*s, h, 0)
            gl.glVertex3f((place+0)*s, h, 0)
        def horiz_ind(place, val, color):
            gl.glColor4f(color[0], color[1], color[2], 1)
            gl.glVertex3f((place+0)*s, 4*h , 0)
            gl.glVertex3f((place+val)*s, 4*h, 0)
            gl.glVertex3f((place+val)*s, 2*h, 0)
            gl.glVertex3f((place+0)*s, 2*h, 0)
        true_speed = np.sqrt(np.square(self.cars[agent_id].hull.linearVelocity[0]) \
            + np.square(self.cars[agent_id].hull.linearVelocity[1]))
        vertical_ind(5, 0.02*true_speed, (1,1,1))
        vertical_ind(7, 0.01*self.cars[agent_id].wheels[0].omega, (0.0,0,1)) # ABS sensors
        vertical_ind(8, 0.01*self.cars[agent_id].wheels[1].omega, (0.0,0,1))
        vertical_ind(9, 0.01*self.cars[agent_id].wheels[2].omega, (0.2,0,1))
        vertical_ind(10,0.01*self.cars[agent_id].wheels[3].omega, (0.2,0,1))
        horiz_ind(20, -10.0*self.cars[agent_id].wheels[0].joint.angle, (0,1,0))
        horiz_ind(30, -0.8*self.cars[agent_id].hull.angularVelocity, (1,0,0))
        gl.glEnd()
        self.score_label.text = "%04i" % self.reward[agent_id]
        self.score_label.draw()

        # Render backwards flag if driving backward and backwards flag render is enabled
        if self.driving_backward[agent_id] and self.backwards_flag:
            pyglet.graphics.draw(3, gl.GL_TRIANGLES,
                                 ('v2i', (W-100, 30,
                                          W-75, 70,
                                          W-50, 30)),
                                 ('c3B', (0, 0, 255) * 3))


if __name__=="__main__":
    from pyglet.window import key
    NUM_CARS = 2  # Supports key control of two cars, but can simulate as many as needed

    # Specify key controls for cars
    CAR_CONTROL_KEYS = [[key.LEFT, key.RIGHT, key.UP, key.DOWN],
                        [key.A, key.D, key.W, key.S]]

    a = np.zeros((NUM_CARS,3))
    def key_press(k, mod):
        global restart, stopped, CAR_CONTROL_KEYS
        if k==0xff1b: stopped = True # Terminate on esc.
        if k==0xff0d: restart = True # Restart on Enter.

        # Iterate through cars and assign them control keys (mod num controllers)
        for i in range(min(len(CAR_CONTROL_KEYS), NUM_CARS)):
            if k==CAR_CONTROL_KEYS[i % len(CAR_CONTROL_KEYS)][0]:  a[i][0] = -1.0
            if k==CAR_CONTROL_KEYS[i % len(CAR_CONTROL_KEYS)][1]: a[i][0] = +1.0
            if k==CAR_CONTROL_KEYS[i % len(CAR_CONTROL_KEYS)][2]:    a[i][1] = +1.0
            if k==CAR_CONTROL_KEYS[i % len(CAR_CONTROL_KEYS)][3]:  a[i][2] = +0.8   # set 1.0 for wheels to block to zero rotation

    def key_release(k, mod):
        global CAR_CONTROL_KEYS

        # Iterate through cars and assign them control keys (mod num controllers)
        for i in range(min(len(CAR_CONTROL_KEYS), NUM_CARS)):
            if k==CAR_CONTROL_KEYS[i % len(CAR_CONTROL_KEYS)][0]  and a[i][0]==-1.0: a[i][0] = 0
            if k==CAR_CONTROL_KEYS[i % len(CAR_CONTROL_KEYS)][1] and a[i][0]==+1.0: a[i][0] = 0
            if k==CAR_CONTROL_KEYS[i % len(CAR_CONTROL_KEYS)][2]:    a[i][1] = 0
            if k==CAR_CONTROL_KEYS[i % len(CAR_CONTROL_KEYS)][3]:  a[i][2] = 0


    env = MultiCarRacing(NUM_CARS)
    env.render()
    for viewer in env.viewer:
        viewer.window.on_key_press = key_press
        viewer.window.on_key_release = key_release
    record_video = False
    if record_video:
        from gym.wrappers.monitor import Monitor
        env = Monitor(env, '/tmp/video-test', force=True)
    isopen = True
    stopped = False
    while isopen and not stopped:
        env.reset()
        total_reward = np.zeros(NUM_CARS)
        steps = 0
        restart = False
        while True:
            s, r, done, info = env.step(a)
            total_reward += r
            if steps % 200 == 0 or done:
                print("\nActions: " + str.join(" ", [f"Car {x}: "+str(a[x]) for x in range(NUM_CARS)]))
                print(f"Step {steps} Total_reward "+str(total_reward))
                #import matplotlib.pyplot as plt
                #plt.imshow(s)
                #plt.savefig("test.jpeg")
            steps += 1
            isopen = env.render().all()
            if stopped or done or restart or isopen == False:
                break
    env.close()
