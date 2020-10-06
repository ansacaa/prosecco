# Procsim

Procsim is a process simulator that uses a BPMN diagram file as an input. Simulations take place in virtual time and a log file is generated with the results obtained.

## Installation

The easiest way to install and use procsim is by using the package manager [pip](https://pip.pypa.io/en/stable/).

```bash
pip install -i https://test.pypi.org/simple/ procsim
```

if you have any problem with the dependencies try running this command:

```bash
pip install pm4pybpmn
pip install simpy
pip install Faker
```

Or you can download the source code from our [Github repository](https://github.com/ansacaa/prosecco) and importit manually.

## Usage

To use procsim first you need to specify which diagram is going to be simulated, such as the properties of the simulation itself. These properties are dictionaries that can be represented an stored on a JSON file (more details on the format of the properties can be found bellow) for testing purposes you can use some of our [example files](https://github.com/ansacaa/prosecco/tree/master/examples). The Properties class is the one in charge of managing all this parameters.

```python
from procsim.properties import Properties
from procsim.simulator import Simulator
import json

diagramPath = "./diagrams/example_diagram.bpmn"
globalProperties = json.load(open('./diagrams/global_properties.json'))
simulationProperties = json.load(open('./diagrams/simulation_properties.json'))

properties = Properties(diagramPath, globalProperties, simulationProperties)
```

As you may see Properties class constructor requires three parameters in order to instatiate it correctly:
1. path: The path were the bpmn file that is about to be simulated is located.
2. globalProperties: These are the properties that configure the whole diagram, e.g. The schedules that are going to be used or the resourses available on a simulation.
3. simultionProperties: These properties are specific for each activity and not the diagram as a whole, e.g. The time distributions for a task duration or the resources a task requires in order to be executed.

Once you have an instance of Properties class you can create a Simulation class instance and call the run method on it.

```python
from datetime import datetime

simulator = Simulator(properties)
simulator.run(datetime(2020, 9, 1), endDate = datetime(2020, 10, 31))
```

The Simulator constructor only requires a Properties instance as a parameter. On the other hand, run method the next parameters that need to be specified:
1. startDate (required): The date when the simulation will start, it can be any day supported by python datetime library.
2. endDate (optional): The date when the simulation will finish. This date represent when process cases will stop being created, but those cases will be finished, so the simulation may finish on a posterior date. Notice that the cases creation will finish on 00:00:00.000 hours of the given date, so that day won't be included.
3. entities (optional): Instead you can specify the number of process cases you want to simulate. If that's the case the simulation will stop when it reachs the specified number, no matter the date.

    NOTE: if neither endDate or entities are specified the simulator will take as endDate the startDate + one week.

## Properties

As mentioned before and as you can see on the example files it's necesary to create some configuration files for the simulator to work correcty. These are the two properties files required.

### Global Properties

This object is the one containing all the information about the environment of the simultaion, but not the simulation itself. Therefore, this configuration can be used on as many diagrams as you want. The attributes required for the dictionary are:
* resources: This is a map containing all the resources that will be available during the simulation process. It is represented on a (key) => (value) mapping, where the key is a string that will work as an identifier for the resource, and the value is an object that has all the properties of that specific resource, which are:
    * id: The identifier of the resource, needs to be the same as the key given before.
    * defaultQuantity: The number of instances of this resource available.
    * defaultCost: The cost of using this resource.
    * defaultTimeTableId: The time table or schedule when the resource will be available.
* timetables: An array where you can specify all the differents schedules that your process or resources will have. Only one time table is required with the id set as 'Default', since this will be the time table used for creating the process cases; all the others tables you want to define are completelly optional. Each element of the array is required to have the following attributes.
    * id: The identifier of the time table.
    * items: An array that contains the time intervals active on the schedule. Each one of the time intervals is an object containing these values:
        * from: The start day of the week for the interval. It has to be a string of the day name in English writen on upper case e.g. "MONDAY" or "SUNDAY".
        * to: The end day of the week for the interval. 
        * beginTime: The hour when the interval begins. It has to be a sting containing the hour on the format HH:MM, seconds are not taken into account for this so they will be ignored.
        * endTime: The hour when the interval finishes.

### Simulation Properties

The simulation properties object contains all the details needed for the simulation to run correctly. This configuration properties are specific for each one of the tasks and, in most of the cases it has to be unique for a diagram. The structure of the file is a map with (key) => (value) format, where the key is the id of the task, event or gateway on the diagram, and value is an object containing the required attributes. 
The value object change depending on whether the node is a task, a gateway or an event. Each one of this requires the following properties:
* Start Event: It is mandatory that the start event is being specified on the simulation properties object, if it is not defined or the simultaor can't find it, the simulation won't take place, the configuration object for the start event requires the following attributes:
    * arrivalRate: An object that defines how the cases will arrive on the simulation, it requires the following properties:
        * unitTime: It can be "HOURS", "MINUTES" or "SECONDS". If another value is given then the default time unit will be "SECONDS".
        * distribution: The probabilistic distribution that will be used for generating the numbers. At this moment only constant and exponential distributions are avaible, but more will be added on further releases.
        * params: The parameters needed to generate the number according to the distibution. This object needs to be differnt for each distribution type.
* Gateway: Not all gateways must have a configuration object defined. Only the ones that choses an outgoing among many, e.g. an Exclusive Gateway that will activate only one outgoing and the other will remain closed. The properties required are written as a (key) => (value) map, where key is the id of the outgoing flow and value is a float describing the probability of chosing that option on a [0,1] range.
* Task: As with the gateways, not all task are required to have a properties object, if no object is defined for a task the simulator will assume it has a 0 seconds duration and that it uses no resources. In case you want to change any of those things on the simulation you will need to add that task to the simulation properties file. The structure is as following:
    * duration: an object that the defines how the duration of the task will be calculated, the format of this object is the same as arrivalRate for a start event.
    * resources: an array containing the id's of the resources this task needs in order to be accomplished.


## License
[APACHE 2.0](https://www.apache.org/licenses/LICENSE-2.0)