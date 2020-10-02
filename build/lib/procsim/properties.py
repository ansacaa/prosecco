from pm4pybpmn.objects.bpmn.importer.bpmn20 import import_bpmn

class Properties:
    def __init__(self, path, globalDict, simulationDict):
        self.graph = import_bpmn(path)
        self.props = self.initializeSimulationProperties(globalDict, simulationDict)
        

    def __translateSchedule(self, schedule):
        daySize = 86400
        offsets = {
            "MONDAY": 0,
            "TUESDAY": 1,
            "WEDNESDAY": 2,
            "THURSDAY": 3,
            "FRIDAY": 4,
            "SATURDAY": 5,
            "SUNDAY": 6
        }
        def translateTimeDayOfWeek(time, dayOfWeek):
            return int(time[:2])*3600 + int(time[-2])*60 + offsets[dayOfWeek]*daySize

        result = [
            [
                translateTimeDayOfWeek(interval['beginTime'], interval['from']), 
                translateTimeDayOfWeek(interval['endTime'], interval['to'])
            ] for interval in schedule['items']
        ]

        result.sort(key= lambda x: x[0])
        return result


    def initializeSimulationProperties(self, globalDict, simulationDict):
        props = {} 
        for prop in globalDict:
            if prop == 'resources':
                props['resources'] = globalDict[prop]
            if prop == 'timeTables':
                props['timeTables'] = dict([(schedule['id'], self.__translateSchedule(schedule)) for schedule in globalDict[prop]])                
        return { 'global': props, 'simulation': simulationDict }
