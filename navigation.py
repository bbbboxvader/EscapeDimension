"""Visibility-graph A* in actor configuration space, using real cover geometry."""
from heapq import heappush, heappop
from math import hypot


class Navigator:
    def __init__(self, solids, bounds, segment_test, half_width=15, head_height=48):
        self.bounds=bounds
        self.segment_test=segment_test
        self.rects=[(l-half_width,b-head_height,r+half_width,t+22) for l,b,r,t in solids]
        self.corners=[]
        for l,b,r,t in self.rects:
            for point in ((l-2,b-2),(l-2,t+2),(r+2,b-2),(r+2,t+2)):
                if self.free(point) and point not in self.corners:
                    self.corners.append(point)
        self.edges=[[] for _ in self.corners]
        for i,a in enumerate(self.corners):
            for j in range(i):
                b=self.corners[j]
                if self.clear(a,b):
                    cost=hypot(a[0]-b[0],a[1]-b[1])
                    self.edges[i].append((j,cost));self.edges[j].append((i,cost))

    def free(self, point):
        x,y=point;left,bottom,right,top=self.bounds
        return (left<=x<=right and bottom<=y<=top
                and not any(l+.01<x<r-.01 and b+.01<y<t-.01 for l,b,r,t in self.rects))

    def clear(self, a, b):
        return not any(self.segment_test(*a,*b,(l+.01,d+.01,r-.01,t-.01)) is not None
                       for l,d,r,t in self.rects)

    def route(self, start, goal):
        if not self.free(start) or not self.free(goal):
            return []
        if self.clear(start,goal):
            return [goal]
        points=self.corners+[start,goal]
        first,last=len(points)-2,len(points)-1
        edges=[list(row) for row in self.edges]+[[],[]]
        for node in (first,last):
            for other in range(node):
                if self.clear(points[node],points[other]):
                    cost=hypot(points[node][0]-points[other][0],points[node][1]-points[other][1])
                    edges[node].append((other,cost));edges[other].append((node,cost))
        todo=[(0,first)];costs={first:0};parents={}
        while todo:
            _,node=heappop(todo)
            if node==last:
                path=[]
                while node!=first:
                    path.append(points[node]);node=parents[node]
                return list(reversed(path))
            for other,cost in edges[node]:
                total=costs[node]+cost
                if total<costs.get(other,float('inf')):
                    costs[other]=total;parents[other]=node
                    heuristic=hypot(points[other][0]-goal[0],points[other][1]-goal[1])
                    heappush(todo,(total+heuristic,other))
        return []
