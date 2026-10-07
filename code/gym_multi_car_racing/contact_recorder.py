"""Read-only physical contact accounting; sensors and same-car fixtures excluded."""
class ContactRecorder:
    def __init__(self):
        self.body_ids = {}
        self.clear_step()

    def bind(self, cars):
        self.body_ids = {hash(body): i for i, car in enumerate(cars)
                         for body in [car.hull] + car.wheels}
        self.clear_step()

    def clear_step(self):
        self.pairs = set()
        self.impulses = {}

    def pair(self, contact):
        a, b = contact.fixtureA, contact.fixtureB
        i, j = self.body_ids.get(hash(a.body)), self.body_ids.get(hash(b.body))
        if i is None or j is None or i == j or a.sensor or b.sensor or not contact.enabled:
            return None
        return tuple(sorted((i, j)))

    def record(self, contact, impulse=None):
        pair = self.pair(contact)
        if pair is not None:
            self.pairs.add(pair)
            if impulse is not None:
                self.impulses[pair] = self.impulses.get(pair, 0.0) + sum(impulse.normalImpulses)

    def snapshot(self, world):
        for contact in world.contacts:
            if contact.touching:
                self.record(contact)
        return [{'agents': list(pair), 'normal_impulse': self.impulses.get(pair, 0.0)}
                for pair in sorted(self.pairs)]
