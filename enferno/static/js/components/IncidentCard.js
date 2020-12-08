Vue.component("incident-card", {
    props: ['incident', 'close', 'log', 'diff', "showEdit"],
    watch: {
        incident: function (b, n) {
            this.loadRevisions();
            if (!this.$root.currentUser.view_simple_history) {
                this.log = false;
            }
            if (this.$root.currentUser.view_full_history) {
                this.diff = true;
            }
        }
    },

    methods: {
        probability(item) {
            return probs[item.probability]
        },


        editAllowed() {
            return this.$root.editAllowed(this.incident) && this.showEdit;
        },


        loadRevisions() {
            axios.get(`/admin/api/incidenthistory/${this.incident.id}`).then(response => {
                this.revisions = response.data.items;
            });
        },

        showDiff(e, index) {

            this.diffDialog = true;
            //calculate diff
            const dp = jsondiffpatch.create({
                arrays: {
                    detectMove: true
                },
                objectHash: function (obj, index) {
                    return obj.name || obj.id || obj._id || '$$index:' + index;
                }
            });

            const delta = dp.diff(this.revisions[index + 1].data, this.revisions[index].data);
            if (!delta) {
                this.diffResult = 'Both items are Identical :)';
            } else {
                this.diffResult = jsondiffpatch.formatters.html.format(delta)
            }

        }

    },

    data: function () {
        return {
            diffResult: '',
            diffDialog: false,
            revisions: null,
            show: false,
        }
    },


    template: `
        <v-card color="grey lighten-3" class="mx-auto pa-3">
            <v-btn v-if="close" @click="$emit('close',$event.target.value)" fab absolute top right x-small text
                   class="mt-6">
                <v-icon>mdi-close</v-icon>
            </v-btn>
            <v-card-text class="d-flex align-center">
                <v-chip small pill label color="gv darken-2" class="white--text">
                    ID {{incident.id}}</v-chip>
                <v-btn v-if="editAllowed()" class="ml-2" @click="$emit('edit',incident)" x-small outlined>Edit</v-btn>

            </v-card-text>
            <uni-field caption="Title" :english="incident.title" :arabic="incident.title_ar"></uni-field>

            <v-card outlined v-if="incident.description" class="ma-2 pa-2" color="grey lighten-5">
                <div class="caption grey--text mb-2">Description</div>
                <div class="rich-description" v-html="incident.description"></div>
            </v-card>

            <v-card outlined class="ma-3" color="grey lighten-5"
                    v-if="incident.potential_violations && incident.potential_violations.length">
                <v-card-text>
                    <div class="px-1 title black--text">Potential Violation Categories</div>
                    <v-chip-group column>
                        <v-chip small color="blue-grey lighten-5" v-for="item in incident.potential_violations"
                                :key="item.id">{{item.title}}</v-chip>
                    </v-chip-group>
                </v-card-text>
            </v-card>

            <v-card outlined class="ma-3" color="grey lighten-5"
                    v-if="incident.claimed_violations && incident.claimed_violations.length">
                <v-card-text>
                    <div class="px-1 title black--text">Claimed Violation Categories</div>
                    <v-chip-group column>
                        <v-chip small color="blue-grey lighten-5" v-for="item in incident.claimed_violations"
                                :key="item.id">{{item.title}}</v-chip>
                    </v-chip-group>
                </v-card-text>
            </v-card>


            <v-card outlined class="ma-3" color="grey lighten-5" v-if="incident.labels && incident.labels.length">
                <v-card-text>
                    <div class="px-1 title black--text">Labels</div>
                    <v-chip-group column>
                        <v-chip small color="blue-grey lighten-5" v-for="label in incident.labels"
                                :key="label.id">{{label.title}}</v-chip>
                    </v-chip-group>
                </v-card-text>
            </v-card>

            <v-card outlined class="ma-3" color="grey lighten-5" v-if="incident.locations && incident.locations.length">
                <v-card-text>
                    <div class="px-1 title black--text">Locations</div>
                    <v-chip-group column>
                        <v-chip small color="blue-grey lighten-5" v-for="item in incident.locations"
                                :key="item.id">{{item.title}}</v-chip>
                    </v-chip-group>
                </v-card-text>
            </v-card>


            <!-- Events -->
            <v-card outlined class="ma-2" color="grey lighten-5" v-if="incident.events && incident.events.length">
                <v-card-text class="pa-2">
                    <div class="px-1 title black--text">Events</div>
                    <event-card v-for="event in incident.events" :key="event.id" :event="event"></event-card>
                </v-card-text>
            </v-card>


            <v-card outlined class="ma-3" v-if="incident.incident_relations && incident.incident_relations.length">
                <v-card-text>
                    <div class="px-1 title black--text">Related Incidents</div>
                    <incident-result class="mt-1" v-for="(item,index) in incident.incident_relations" :key="index"
                                     :incident="item.incident">
                        <template v-slot:header>

                            <v-sheet color="yellow lighten-5" class="pa-2">

                                <div class="caption ma-2">Relationship Info</div>
                                <v-chip color="grey lighten-4" small label>{{probability(item)}}</v-chip>
                                <v-chip color="grey lighten-4" small label>{{item.comment}}</v-chip>

                            </v-sheet>

                        </template>
                    </incident-result>
                </v-card-text>
            </v-card>

            <v-card outlined class="ma-3" v-if="incident.bulletin_relations && incident.bulletin_relations.length">

                <v-card-text>
                    <div class="px-1 title black--text">Related Bulletins</div>
                    <bulletin-result class="mt-1" v-for="(item,index) in incident.bulletin_relations" :key="index"
                                     :bulletin="item.bulletin">
                        <template v-slot:header>

                            <v-sheet color="yellow lighten-5" class="pa-2">

                                <div class="caption ma-2">Relationship Info</div>
                                <v-chip color="grey lighten-4" small label>{{probability(item)}}</v-chip>
                                <v-chip color="grey lighten-4" small label>{{item.comment}}</v-chip>

                            </v-sheet>

                        </template>
                    </bulletin-result>
                </v-card-text>
            </v-card>

            <v-card outlined class="ma-3" v-if="incident.actor_relations && incident.actor_relations.length">
                <v-card-text>
                    <div class="px-1 title black--text">Related Actors</div>
                    <actor-result class="mt-1" v-for="(item,index) in incident.actor_relations" :key="index"
                                  :actor="item.actor">
                        <template v-slot:header>

                            <v-sheet color="yellow lighten-5" class="pa-2">

                                <div class="caption ma-2">Relationship Info</div>
                                <v-chip color="grey lighten-4" small label>{{probability(item)}}</v-chip>
                                <v-chip color="grey lighten-4" small label>{{item.comment}}</v-chip>

                            </v-sheet>

                        </template>
                    </actor-result>
                </v-card-text>
            </v-card>

            <v-card v-if="incident.review" outline elevation="0" class="ma-3" color="light-green lighten-5">
                <v-card-text>
                    <div class="px-1 title black--text">Review</div>
                    <div v-html="incident.review" class="pa-1 my-2 grey--text text--darken-2">

                    </div>
                    <v-chip small label color="lime">{{incident.review_action}}</v-chip>
                </v-card-text>
            </v-card>


            <v-card v-if="log" outline elevation="0" color="ma-3">
                <v-card-text>
                    <h3 class="title black--text">Log History</h3>

                    <template v-for="(revision,index) in revisions">
                        <v-sheet color="grey lighten-4" dense flat class="my-1 pa-2 d-flex align-center">
                            <span class="caption">{{revision.data['comments']}} - <v-chip x-small label
                                                                                          color="gv lighten-3">{{revision.data.status}}</v-chip> - {{revision.created_at}}
                                - By {{revision.user.email}}</span>
                            <v-spacer></v-spacer>

                            <v-btn v-if="diff" v-show="index!=revisions.length-1" @click="showDiff($event,index)"
                                   class="mx-1" color="grey" icon small>
                                <v-icon>mdi-compare</v-icon>
                            </v-btn>

                        </v-sheet>

                    </template>
                </v-card-text>

            </v-card>
            <v-dialog
                    v-model="diffDialog"
                    max-width="770px"
            >
                <v-card class="pa-5">
                    <v-card-text>
                        <div v-html="diffResult">

                        </div>
                    </v-card-text>
                </v-card>

            </v-dialog>


            <!-- Root Card   -->
        </v-card>
    `
});
  