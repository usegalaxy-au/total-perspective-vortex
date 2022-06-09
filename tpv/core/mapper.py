import functools
import logging
import re

from .entities import Tool
from .loader import TPVConfigLoader

log = logging.getLogger(__name__)


class EntityToDestinationMapper(object):

    def __init__(self, loader: TPVConfigLoader):
        self.loader = loader
        self.entities = {
            "tools": loader.tools,
            "users": loader.users,
            "roles": loader.roles
        }
        self.destinations = loader.destinations
        self.default_inherits = loader.global_settings.get('default_inherits')
        self.lookup_tool_regex = functools.lru_cache(maxsize=None)(self.__compile_tool_regex)
        self.inherit_matching_entities = functools.lru_cache(maxsize=None)(self.__inherit_matching_entities)

    def __compile_tool_regex(self, key):
        return re.compile(key)

    def _find_entities_matching_id(self, entity_list, entity_name):
        matches = []
        for key in entity_list.keys():
            if self.lookup_tool_regex(key).match(entity_name):
                matches.append(entity_list[key])
        if not matches and self.default_inherits:
            default_match = entity_list.get(self.default_inherits)
            if default_match:
                matches.append(default_match)
        return matches

    def __inherit_matching_entities(self, entity_type, entity_name):
        entity_list = self.entities.get(entity_type)
        matches = self._find_entities_matching_id(entity_list, entity_name)
        return self.inherit_entities(matches)

    def evaluate_entity_early(self, entities, entity, context):
        context.update({
            'entities': entities,
            'entity': entity,
            'self': entity
        })
        return entity.evaluate_early(context)

    def evaluate_entities_early(self, entities, context):
        return [self.evaluate_entity_early(entities, entity, context) for entity in entities]

    def inherit_entities(self, entities):
        if entities:
            return functools.reduce(lambda a, b: b.inherit(a), entities)
        else:
            return None

    def combine_entities(self, entities):
        if entities:
            return functools.reduce(lambda a, b: a.combine(b), entities)
        else:
            return None

    def rank(self, entity, destinations, context):
        return entity.rank_destinations(destinations, context)

    def find_best_matches(self, entity, destinations, context):
        matches = [dest for dest in destinations.values() if entity.matches(dest, context)]
        return self.rank(entity, matches, context)

    def configure_gxy_destination(self, gxy_destination, entity):
        if entity.env:
            gxy_destination.env += [dict(name=k, value=v) for (k, v) in entity.env.items()]
        gxy_destination.params.update(entity.params or {})
        if entity.resubmit:
            gxy_destination.resubmit += entity.resubmit.values()
        return gxy_destination

    def _find_matching_entities(self, tool, user):
        tool_entity = self.inherit_matching_entities("tools", tool.id)
        if not tool_entity:
            tool_entity = Tool.from_dict(self.loader, {'id': tool.id})

        entity_list = [tool_entity]

        if user:
            role_entities = (self.inherit_matching_entities("roles", role.name)
                             for role in user.all_roles() if not role.deleted)
            # trim empty
            user_role_entities = (role for role in role_entities if role)
            user_role_entity = next(user_role_entities, None)
            if user_role_entity:
                entity_list += [user_role_entity]

            user_entity = self.inherit_matching_entities("users", user.email)
            if user_entity:
                entity_list += [user_entity]

        return entity_list

    def map_to_destination(self, app, tool, user, job):
        # 1. Find the entities relevant to this job
        entity_list = self._find_matching_entities(tool, user)

        # 2. Create evaluation context - these are the common variables available within any code block
        context = {
            'app': app,
            'tool': tool,
            'user': user,
            'job': job,
            'mapper': self
        }

        # 3. Evaluate entity properties that must be evaluated early, prior to combining
        early_evaluated_entities = self.evaluate_entities_early(entity_list, context)

        # 4. Combine entity requirements
        combined_entity = self.combine_entities(early_evaluated_entities)

        context.update({
            'entity': combined_entity,
            'self': combined_entity
        })

        # 5. Evaluate remaining expressions after combining requirements
        late_evaluated_entity = combined_entity.evaluate_late(context)

        context.update({
            'entity': late_evaluated_entity,
            'self': late_evaluated_entity
        })

        # 6. Find best matching destinations
        ranked_dest_entities = self.find_best_matches(late_evaluated_entity, self.destinations, context)

        # 7. Return galaxy destination with params added
        if ranked_dest_entities:
            for d in ranked_dest_entities:
                try:  # An exception here signifies that a destination rule did not match
                    # Evaluate the destinations as regular entities
                    early_evaluated_destination = self.evaluate_entity_early([d, late_evaluated_entity], d, context)
                    dest_combined_entity = early_evaluated_destination.combine(late_evaluated_entity)
                    final_combined_entity = dest_combined_entity.evaluate_late(context)
                    gxy_destination = app.job_config.get_destination(d.id)
                    return self.configure_gxy_destination(gxy_destination, final_combined_entity)
                except Exception as e:
                    log.debug(f"Destination entity: {d} matched but could not fulfill requirements due to: {e}")

        # 8. No matching destinations. Throw an exception
        from galaxy.jobs.mapper import JobMappingException
        raise JobMappingException(f"No destinations are available to fulfill request: {late_evaluated_entity.id}")
