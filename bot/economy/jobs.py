from bot.economy.economy_objects import Job

# List of all jobs
# Job name, description, salary in dollars (will get converted to cents for storage)
jobs = [
    Job("Taxi Driver", "Drive people around in a taxi", 100),
    Job("Truck Driver", "Drive around in a truck, hauling goods", 100),
    Job("Lawyer", "Get people out of prison sentences", 200),
    Job("Police Officer", "Enforce the law", 200),
    Job("Software Engineer", "Write code", 150),
    Job("Chef", "Cook food", 100),
    Job("Doctor", "Heal people", 200),
    Job("Emergency Services", "Help people in an emergency", 200),
    Job("Firefighter", "Fight fires", 150),
    Job("Office Worker", "Work in an office", 125),
]

unemployed = Job("Unemployed", "No job", 0)


def get_job_from_str(name: str) -> Job | None:
    if name == "Unemployed":
        return unemployed
    for job in jobs:
        if job.name == name:
            return job
    return None
