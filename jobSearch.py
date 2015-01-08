import json
import requests
import datetime
import sys
from operator import itemgetter, attrgetter

# Class to represent the job candidate
class JobProfile:
    
    def __init__(self, file_name):
        try:
            # open json file and parse out candidate information
            candidate_json = json.load(open(file_name))
            self.name = candidate_json['name']
            print "Creating Job Profile for %s..." % self.name
            self.location = candidate_json['location']
            self.type = candidate_json['type']
            self.skills = set()
            for skill in candidate_json['skills']:
                self.skills.add(skill.lower())
        except Exception as e:
            print "Error in creating job profile: "+ str(e.message)
            sys.exit()

# Class to represent each startup 
class Startup:

    def __init__(self, name, description, url, _id, quality, skillMatch, followerCount, position):
        self.name = name
        self.description = description
        self.url = url
        self._id = _id
        self.quality = quality
        self.skillMatch = skillMatch
        self.followerCount = followerCount
        self.positions = []
        self.positions.append(position)

# Class to present the API functionality we will use 
class AngelListAPI:

    # private attributes
    __recommended = dict()
    __candidate = None
    locationId = 0

    def __init__(self, candidate):
        self.__candidate = candidate
        self.locationId = self.__retrieve_location_tag(candidate.location)
        self.__check_startups()

    def recommend(self):
        recommended = [self.__recommended[key] for key in self.__recommended]
        # sorted by match score = (quality/2) + (2*skillMatch) and then sorted by followerCount
        recommended.sort(key = lambda startup: (startup.quality/2 + 2*startup.skillMatch, startup.followerCount))
        recommended.reverse()
        print "We Recommend These Startups:\n"
        for i in range(1,11):
            startup = recommended[i]
            print "%i. %s: %s" % (i, startup.name.encode('ascii', 'ignore'), startup.description.encode('ascii', 'ignore'))
            print "\tMatch Score: %i" % (startup.quality/2 + (2*startup.skillMatch))
            print "\tFollowers: %i" % startup.followerCount
            print "\tPositions: " + str(startup.positions)
            print "\tCheck Them Out At %s\n" % startup.url.encode('ascii', 'ignore')

    # Description: retrieves and adds startups in provided location to the recommended list
    # Parameter: None
    # Returns: Void (adds valid startups to the recommended list)
    def __check_startups(self):
        request = requests.get('https://api.angel.co/1/tags/%i/jobs' % self.locationId)
        startupsJson = request.json()
        pages = startupsJson['last_page']   
        print "Analyzing ~%i Startups in %s..." % (50*pages,self.__candidate.location)
        # make request for every page of jobs in provided location
        for i in range(1, pages):
            page_request = requests.get('https://api.angel.co/1/tags/%i/jobs?page=%i' % (self.locationId, i))
            startupsJson = page_request.json()
            self.__evaluate_startup(startupsJson['jobs'])

    # Description: retrieves job & startup info and adds valid startups to recommended list
    # Parameter: AngelListAPI Jobs (JSONArray)
    # Returns: Void (adds valid startups to the recommended list)
    def __evaluate_startup(self, jobsJson):
            for jobJson in jobsJson:
                # filter jobs by what candidate is looking for (internship/full-time)
                if jobJson['job_type'] == self.__candidate.type:
                    # this startup has already been saved
                    if jobJson['startup']['id'] in self.__recommended.keys():
                        # update skills match for startup
                        skillMatch = self.__match_skills(jobJson['tags'])   
                        if skillMatch > 0:              
                            startup = self.__recommended[jobJson['startup']['id']]
                            startup.skillMatch = startup.skillMatch + skillMatch
                            startup.positions.append(jobJson['title'])
                            self.__recommended[jobJson['startup']['id']] = startup
                    else:
                        # startup seen for first time
                        startupJson = jobJson['startup']
                        skillMatch = self.__match_skills(jobJson['tags'])
                        # validate (community profile = false and hidden = false)
                        if startupJson['hidden'] == False and startupJson['community_profile'] == False:
                            startup = Startup(startupJson['name'],startupJson['high_concept'],
                                              startupJson['company_url'], startupJson['id'], 
                                              startupJson['quality'], skillMatch, 
                                              startupJson['follower_count'], jobJson['title'])
                            # add to recommended list
                            self.__recommended[startupJson['id']] = startup
                        else:
                            #print "%s: Unverified Company" % startupJson['name']
                            pass

    # Description: calculates number of skills candidate has in common with job requirements
    # Parameter: AngelListAPI Tags (JSONArray)
    # Returns: number of matching skills (Integer)
    def __match_skills(self, tagsJson):     
        jobSkills = set()
        # match skills with job 
        for tagJson in tagsJson:
            jobSkills.add(tagJson['name'])

        return len((self.__candidate.skills).intersection(jobSkills))
        
    # Description: retrieves location tag id from AngelListAPI for provided location
    # Parameter: location for interested job opportunities (String)
    # Returns: AngelListAPI tag id (Integer)
    def __retrieve_location_tag(self, location):
        try:
            requestUrl = 'https://api.angel.co/1/search?query=%s&type=%s' % (location, "LocationTag")
            request = requests.get(requestUrl)
            data_json = request.json()
            if len(data_json) == 0:
                print "Invalid Location!"
            else:
                tag = data_json[0]
                return tag['id']
        except Exception as e:
            print "Error in retrieving location tag: "+ str(e.message)
            sys.exit()

def main():
    candidate = JobProfile(sys.argv[1])
    API = AngelListAPI(candidate)
    API.recommend()

if __name__ == "__main__":
    main()
