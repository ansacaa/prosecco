from simpy import Environment, Resource, PreemptiveResource, Store, PriorityStore
from simpy.events import AllOf, AnyOf, Event
from simpy.exceptions import Interrupt
#from random import expovariate, normalvariate, randint, random, seed

from datetime import timedelta
from faker import Faker

import copy
import random

fake = Faker()


class Simulator:
  def __init__(self, props):
    self.processGraph = props.graph
    self.props = props.props
    self.generators = {
      'startEvent': self.startEventGenerator,
      'endEvent': self.endEventGenerator,
      'task': self.taskGenerator,
      'userTask': self.taskGenerator,
      'sendTask': self.taskGenerator,
      'receiveTask': self.taskGenerator,
      'parallelGateway': self.parallelGatewayGenerator,
      'exclusiveGateway': self.exclusiveGatewayGenerator,
      'inclusiveGateway': self.inclusiveGatewayGenerator
    }

    self.orJoins = dict([(orJoin, self.initiateOrJoin(orJoin)) for orJoin in self.processGraph.get_nodes_id_list_by_type("inclusiveGateway")])
    self.env = Environment()
    self.resources = dict()
    self.timeTables = dict()
    self.schedules = copy.deepcopy(self.props['global']['timeTables'])
    

  def getDurationTime(self, durationProps):
    result = 0
    distribution = "" if 'distribution' not in durationProps else durationProps['distribution']
    params = durationProps['params']
    if distribution == "constantDistribution":
      result = params['constantValue']
    elif distribution == 'normalDistribution':
      result = random.normalvariate(params['mean'],params['standard_deviation'])
    elif distribution == "exponentialDistribution":
      result = random.expovariate(1.0 / params['mean'])
    elif distribution == "uniformDistribution":
      result = random.uniform(params['low'],params['high'])
    elif distribution == "triangularDistribution":
      result = random.triangular( params['low'],params['high'],params['mode'])
    
    if 'timeUnit' in durationProps:
      if durationProps['timeUnit'] == "MINUTES":
        result *= 60
      if durationProps['timeUnit'] == "HOURS":
        result *= 3600

    return result

  # not used !!!???
  def possibleToComplete(self, resource, duration):
    result = 0
    for schedule in self.schedules[resource.timetable]:
        if(schedule[1] >= self.env.now):
            result = 0 if schedule[1] - self.env.now >= duration else schedule[1]
            break
    return result

  def startEventGenerator(self, node, flows, simProps, entityObject):
    yield self.env.timeout(entityObject['start'])
    thisMoment = self.startDate + timedelta(days = self.env.now/86400 - self.daysOffset)
    
    taskObject = self.TaskEvent(node,0,0,None,entityObject['caseId'])
    self.logger.write(taskObject, None, "start")
    for outgoing in node[1]['outgoing']:
      self.update(outgoing, 1, entityObject['orJoins'])
      flows[outgoing].succeed()
  
  def endEventGenerator(self, node, flows, simProps, entityObject):
    yield AnyOf(self.env, [flows[incoming] for incoming in node[1]['incoming']])
    thisMoment = self.startDate + timedelta(days = int(self.env.now)/86400 - self.daysOffset)
    taskObject = self.TaskEvent(node,0,0,None,entityObject['caseId'])
    self.logger.write(taskObject, None, "complete")
    
  def activityGenerator(self, node, flows, simProps, entityObject):
    while True:
      duration = 0 if "duration" not in simProps else self.getDurationTime(simProps["duration"])
      
      #Wait for previous activities
      yield AllOf(self.env, [flows[incoming] for incoming in node[1]['incoming']])
      
      #Request resources
      res, req = None, None
      
      if 'resources' in simProps and len(simProps['resources']) > 0: 
        res = yield self.resources[simProps['resources'][0]].get()
        req = res.request(priority=100) 
        while True:
          try:
            yield req
            break
          except Interrupt as interrupt:
            req = res.request(priority=100)
      
      #Log Writing Start
      resourceName = "NULL" if res is None else res.name
      resourceRole = "NULL" if res is None else res.role
      thisMoment = self.startDate + timedelta(days = int(self.env.now)/86400 - self.daysOffset)
      # self.log.write(thisMoment.isoformat() + ";"  + node[1]['node_name'] + ";" + str(entityObject['caseId']) + ";" + str(resourceName) + ";" + str(resourceRole) + ";start\n")
      
      #Simulate time spend
      while duration > 0:
        try:
          yield self.env.timeout(duration)
          duration = 0
        except Interrupt as interrupt:
          usage = self.env.now - interrupt.cause.usage_since
          duration = duration - usage
          if(duration > 0):
            req = res.request(priority=100)
            yield req

      #Log Writting complete
      thisMoment = self.startDate + timedelta(days = int(self.env.now)/86400 - self.daysOffset)
      # self.log.write(thisMoment.isoformat() + ";"  + node[1]['node_name'] + ";" + str(entityObject['caseId']) + ";" + str(resourceName) + ";" + str(resourceRole) + ";complete\n")
      
      #Relese further activities
      if res is not None:
        res.release(req)
        self.resources[simProps['resources'][0]].put(res)
          
      for outgoing in node[1]['outgoing']:
        self.update(outgoing, 1, entityObject['orJoins'])
          
      for incoming in node[1]['incoming']:
        self.update(incoming, -1, entityObject['orJoins'])
        flows[incoming] = self.env.event()
          
      for outgoing in node[1]['outgoing']:
        flows[outgoing].succeed()

  def exclusiveGatewayGenerator(self, node, flows, simProps, entityObject):
    while True:
      eventTrigger = yield AnyOf(self.env, [flows[incoming] for incoming in node[1]['incoming']])
      activatedFlows = eventTrigger.events

      selectedFlow = node[1]['outgoing'][0]      
      if len(node[1]['outgoing']) > 1:
        randVar, acc = random.random(), 0
        for outgoing in simProps:
          acc += simProps[outgoing]
          if randVar <= acc:
            selectedFlow = outgoing
            break
                
      self.update(selectedFlow, 1, entityObject['orJoins'])
      for incoming in node[1]['incoming']:
        if flows[incoming] in activatedFlows:
          self.update(incoming, -1, entityObject['orJoins'])
          flows[incoming] = self.env.event()

      flows[selectedFlow].succeed()

  def parallelGatewayGenerator(self, node, flows, simProps, entityObject):
    while True:
      yield AllOf(self.env, [flows[incoming] for incoming in node[1]['incoming']])
      
      for outgoing in node[1]['outgoing']:
          self.update(outgoing, 1, entityObject['orJoins'])
        
      for incoming in node[1]['incoming']:
        self.update(incoming, -1, entityObject['orJoins'])
        flows[incoming] = self.env.event()

      for outgoing in node[1]['outgoing']:
        flows[outgoing].succeed()

  def inclusiveGatewayGenerator(self, node, flows, simProps, entityObject):
    while True:
      yield AnyOf(self.env, [flows[incoming] for incoming in node[1]['incoming']])
      
      while not self.isEnabled(self.processGraph.get_flows(), entityObject['orJoins'][node[1]['id']]['s'], node[1]['id']):
        yield entityObject['orJoins'][node[1]['id']]['updateFlowEvent']

      selectedFlow = node[1]['outgoing'][0]    
      if len(node[1]['outgoing']) > 1:
        randVar, acc = random.random(), 0
        for outgoing in simProps:
          acc += simProps[outgoing]
          if randVar <= acc:
            selectedFlow = outgoing
            break
      self.update(selectedFlow, 1, entityObject['orJoins'])

      for incoming in node[1]['incoming']:
        self.update(incoming, -1, entityObject['orJoins'])
        flows[incoming] = self.env.event()
      flows[selectedFlow].succeed()

  def cases(self, startEvents, endDate, entities):
    # NOTE: Veriy if there´s no start event and handle that exception
    if 'arrivalRate' not in self.props['simulation'][startEvents[0]]:
      return []
    
    arrivalRate = self.props['simulation'][startEvents[0]]['arrivalRate']
    caseId = 1
    result = []
    week = 0
    endTime = (endDate - self.startDate).days * 86400 + self.daysOffset * 86400 if endDate else float('inf')
    entities = entities if entities else float('inf')
    startTime = self.daysOffset * 86400
    while startTime < endTime and caseId <= entities:
      for interval in self.schedules['Default']:
        startTime = max(interval[0] + week * 86400*7, startTime)
        while startTime < interval[1] + week * 86400*7 and startTime < endTime and caseId < entities:
          result.append((caseId, startTime))
          startTime += self.getDurationTime(arrivalRate)
          caseId += 1
      week += 1
    return result

  def run(self, startDate, endDate=None, entities=None):
    self.startDate = startDate
    self.daysOffset = startDate.weekday()
    self.logger = self.Logger(startDate, self.daysOffset, self.env)
    self.resourceCreator()
    startCases = self.cases(self.processGraph.get_nodes_id_list_by_type('startEvent'), endDate, entities)
    for caseId, startTime in startCases:
      caseObject = {}
      flows = {}
      caseObject['caseId']=caseId
      caseObject['orJoins']=copy.deepcopy(self.orJoins)

      for orjoin in caseObject['orJoins']:
          caseObject['orJoins'][orjoin]['updateFlowEvent'] = self.env.event()

      for flow in self.processGraph.get_flows():
          flows[flow[2]['id']] = self.env.event()

      for node in self.processGraph.get_nodes():
        nodeProps = {}
        if node[1]['id'] in self.props['simulation']:
          nodeProps = self.props['simulation'][node[1]['id']]
        if node[1]['type'] == 'startEvent':
          caseObject['start'] = startTime
        self.env.process(self.generators[node[1]['type']](node, flows, nodeProps, caseObject))
    self.env.run(until = 10000000)
    self.logger.close()

  def scheduleControl(self, schedule, events):
    currentWeek = 0
    for resource in events:
      req = resource.request(priority=50)
      yield req
      resource.req = req
    while True: 
      weekAddition = 86400 * 7 * currentWeek
      yield self.env.timeout(weekAddition - self.env.now)
      for interval in schedule:
        if self.env.now < interval[0] + weekAddition:
            yield self.env.timeout((interval[0] + weekAddition) - self.env.now)
        for resource in events:
            resource.release(resource.req)
            resource.req = None
        if self.env.now < interval[1] + weekAddition:
            yield self.env.timeout((interval[1] + weekAddition) - self.env.now)
        for resource in events:
          req = resource.request(priority=50)
          yield req
          resource.req = req
      currentWeek+=1

  def createResources(self):
    for resource in self.props['global']['resources']:
        res = self.props['global']['resources'][resource]
        defaultQuantity = int(res['defaultQuantity'])
        self.resources[resource] = Store(self.env, defaultQuantity)

        timetable = res['defaultTimetableId']
        if timetable not in self.timeTables:
            self.timeTables[timetable] = []
            
        for _n in range(defaultQuantity):
            resourceItem = PreemptiveResource(self.env, 1) 
            if 'generateName' in res:
              resourceItem.name = resource.id + '_' + f'{_n:02d}'
            else:
              resourceItem.name = fake.name()
            resourceItem.role = res['id']
            resourceItem.timetable = res['defaultTimetableId']
            self.resources[resource].put(resourceItem)
            self.timeTables[timetable].append(resourceItem)


  # =======================================================
  # New support for orJoin
  # =======================================================

  def isEnabled(self, edges, s, j):
    red = [(src, tgt) for (src, tgt) in s if tgt == j and s[(src,tgt)] > 0]
    counter = 0
    while counter < len(red):
        (edgesrc, edgtgt) = red[counter]
        counter+=1
        red.extend([(src, tgt) for (src, tgt) in s if tgt == edgesrc and (src, tgt) not in red and tgt != j])
    green = [(src, tgt) for (src, tgt) in s if tgt == j and s[(src, tgt)] == 0]
    counter = 0
    while counter < len(green):
        (edgesrc, edgtgt) = green[counter]
        counter+=1
        green.extend([(src, tgt) for (src, tgt) in s if tgt == edgesrc and (src, tgt) not in red and (src, tgt) not in green and tgt != j])
    return len(set(green).intersection([(src, tgt) for (src, tgt) in s if s[(src, tgt)] > 0])) == 0
  
  def update(self, flow_id, value, orJoins):
    flow = self.processGraph.get_flow_by_id(flow_id)
    for orjoin in orJoins:
        s = orJoins[orjoin]['s']
        if (flow[2]['sourceRef'], flow[2]['targetRef']) in s:
          s[(flow[2]['sourceRef'], flow[2]['targetRef'])] += value
        else: 
          s[(flow[2]['sourceRef'], flow[2]['targetRef'])] = value

        s[(flow[2]['sourceRef'], flow[2]['targetRef'])] = max(s[(flow[2]['sourceRef'], flow[2]['targetRef'])],0)
        orJoins[orjoin]['updateFlowEvent'].succeed()
        orJoins[orjoin]['updateFlowEvent'] = self.env.event()

  def initiateOrJoin(self, orJoin):
    return {
      's': dict([((flow['sourceRef'], flow['targetRef']), 0) for (_,_,flow) in self.processGraph.get_flows()])
    }

# =======================================================
# New classes and generators for priorities and life cicle
# =======================================================

  def taskGenerator(self, node, flows, simProps, entityObject):
    taskstore = None
    node[1]['priority'] = simProps['priority'] if 'priority' in simProps else 1
    if 'resources' in simProps and len(simProps['resources']) > 0:
      taskstore=self.resources[simProps['resources'][0]]

    while True:
      duration = 0 if "duration" not in simProps else self.getDurationTime(simProps["duration"])
      
      #Wait for previous activities

      yield AllOf(self.env, [flows[incoming] for incoming in node[1]['incoming']])

      # LOG FOR SCHEDULE
      resumeEvent = self.env.event()
      taskEvent = self.TaskEvent(node, self.env.now, duration, resumeEvent, entityObject['caseId'])
      self.logger.write(taskEvent, None, "schedule")

      #Add task to the store to get resource
      #First create an event that will be triggered when the task is selected for a resource
      if taskstore is not None:  
        taskstore.put(taskEvent)
        yield resumeEvent
      else:
        self.logger.write(taskEvent, None, "start")
        yield self.env.timeout(duration)
        self.logger.write(taskEvent, None, "complete")
      
      #Relese further activities     
      for outgoing in node[1]['outgoing']:
        self.update(outgoing, 1, entityObject['orJoins'])
          
      for incoming in node[1]['incoming']:
        self.update(incoming, -1, entityObject['orJoins'])
        flows[incoming] = self.env.event()
          
      for outgoing in node[1]['outgoing']:
        flows[outgoing].succeed()
  
  class Resource:
    def __init__(self, env, name, taskStore, schedule, logger):
        self.env = env
        self.name = name
        self.offset = 0
        self.taskStore = taskStore
        self.schedule = schedule
        self.currentSchedule = schedule[0] if len(schedule) > 0 else [0, float('inf')]
        self.currentScheduleIndex = 0 if len(schedule) > 0 else -1
        self.currentWeek = 0
        self.logger = logger
        
    def _changeSchedule(self):
        self.currentScheduleIndex += 1
        if self.currentScheduleIndex == len(self.schedule):
            self.currentScheduleIndex = 0
            self.currentWeek += 1
        self.currentSchedule = [
            time+(self.currentWeek*86400*7) for time in self.schedule[self.currentScheduleIndex]
        ]
        return self.currentSchedule[0] - self.env.now if self.env.now < self.currentSchedule[0] else 0
    
    def _getSimulationStep(self, duration):
      val = min(duration, self.currentSchedule[1] - self.env.now) if self.currentSchedule[1] > self.env.now else 0
      return val

    def run(self):
        while True:
            #Verify if it has not get to the schedule start yet
            if self.env.now < self.currentSchedule[0]:
                yield self.env.timeout(self.currentSchedule[0] - self.env.now)
            #Verify if it is on the schedule
            if self.env.now > self.currentSchedule[1]:
                yield self.env.timeout(self._changeSchedule())

            #Get a task from the store
            task = yield self.taskStore.get()
            self.logger.write(task, self, "assign")
            simulated = 0
            missing = task.duration
            self.logger.write(task, self, "start")
            while simulated < task.duration: 
                step = self._getSimulationStep(missing)
                yield self.env.timeout(step)
                simulated += step
                missing -= step
                if simulated < task.duration:
                    waitForNextScheduleStart = self._changeSchedule()
                    # if wait=0 then actually there is no suspension of the task
                    if waitForNextScheduleStart > 0: 
                      self.logger.write(task, self, "suspend")
                      yield self.env.timeout(waitForNextScheduleStart)
                      self.logger.write(task, self, "resume")

            self.logger.write(task, self, "complete")
            task.event.succeed()
            
  class TaskEvent:
      def __init__(self, node, time, duration, event, caseId):
          self.priority = node[1]['priority'] if 'priority' in node[1] else 1
          self.time = time
          self.duration = duration
          self.event = event
          self.name = node[1]['node_name']
          self.caseId = caseId
          
      def __lt__(self, other):
          return self.priority < other.priority if self.priority != other.priority else self.time < other.time

  def resourceCreator(self):
    for resource in self.props['global']['resources']:
        res = self.props['global']['resources'][resource]
        defaultQuantity = int(res['defaultQuantity'])
        self.resources[resource] = PriorityStore(self.env, defaultQuantity)

        timetable = res['defaultTimetableId']
            
        for _n in range(defaultQuantity):
            if 'generateName' in res:
              name = res['id'] + '_' + f'{_n:02d}'
            else:
              name = fake.name()
            resourceItem = self.Resource(self.env, name, self.resources[resource], self.schedules[timetable], self.logger)
            self.env.process(resourceItem.run())

  class Logger:
    def __init__(self, startDate, daysOffset, env):
      self.startDate = startDate
      self.daysOffset = daysOffset
      self.env = env
      self.log = open("simulation_log.csv", "w")
      self.log.write("timestamp;activity_name;case;resource;role;event_type\n")
    
    def write(self, task, resource, event):
      thisMoment = self.startDate + timedelta(days = self.env.now/86400 - self.daysOffset)
      resourceName = resource.name if resource is not None else "NULL"
      self.log.write(thisMoment.isoformat() + ";"  + task.name + ";" + str(task.caseId) + ";NULL" + ";" + resourceName +";" + event + "\n")

    def close(self):
      self.log.close()
