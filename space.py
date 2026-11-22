"""Quarter-turn geometry shared by the camera and gravity simulation."""
from functools import wraps


def turn_point(x, y, turns):
    """Clockwise quarter turns about the origin; also works for vectors."""
    return ((x,y),(y,-x),(-x,-y),(-y,x))[turns%4]


def turn_box(box, turns):
    a,b,c,d=box
    points=[turn_point(x,y,turns) for x,y in ((a,b),(a,d),(c,b),(c,d))]
    return min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)


def gravity_frame(method):
    """Reuse the 2D solver in screen axes, then restore world coordinates.

    Bodies, cover and swept projectiles all use exactly the same orthogonal
    transform. This avoids a second, slightly different sideways-gravity solver.
    """
    @wraps(method)
    def wrapped(self,*args,**kwargs):
        turns=self.view_turn if not self._local_depth else 0
        if not turns:return method(self,*args,**kwargs)
        args=list(args)
        if method.__name__=='safe_position':
            x,y=turn_point(*(args[:2] if len(args)>=2 else (kwargs['x'],kwargs['y'])),turns)
            if len(args)>=2:args[:2]=[x,y]
            else:kwargs.update(x=x,y=y)
        aim_index=2 if method.__name__=='tick' else 0 if method.__name__ in ('shoot','throw','throw_knife') else None
        if aim_index is not None:
            if len(args)>aim_index:args[aim_index]=turn_point(*args[aim_index],turns)
            elif 'aim' in kwargs:kwargs['aim']=turn_point(*kwargs['aim'],turns)
            elif method.__name__=='tick':kwargs['aim']=turn_point(900,300,turns)
        levels=self.levels
        player=self.player
        self._local_depth+=1
        self.transform_scene(turns)
        try:return method(self,*args,**kwargs)
        finally:
            if self.player is player:self.transform_scene(-turns)
            self.levels=levels
            self._local_depth-=1
    return wrapped
