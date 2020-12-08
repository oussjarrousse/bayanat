Vue.component('incident-search-box', {
    props: {
        value: {
            type: Object,
            required: true
        },
        users: {
            type: Array
        },
        closeBtn: {
            type: String
        },
        extraFilters: {
            type: Boolean
        },
        i18n: {
            type: Object
        }
    },

    data: () => {
        return {
            repr: '',
            q: {},





        }
    },
    watch: {


        q: {
            handler(newVal) {

                this.$emit('input', newVal)
            }
            ,
            deep: true
        },
        value: function (newVal, oldVal) {


            if (newVal != oldVal) {
                this.q = newVal;
            }
        }

    },
     created() {
        this.q = this.value;

    },
    methods: {

    },

    template: `
        <v-card outlined class="pa-7">

            <v-btn v-if="closeBtn" absolute top right @click="$emit('close')" icon>
                <v-icon>mdi-close</v-icon>
            </v-btn>


            <v-container class="fluid">
                <v-row>
                    <v-col>

                        <v-text-field

                                v-model="q.tsv"
                                :label="i18n.contains_"
                                clearable
                                @keydown.enter="$emit('search',q)"
                        ></v-text-field>

                        <v-text-field

                                v-model="q.extsv"
                                :label="i18n.notContains_"
                                clearable
                        ></v-text-field>
                    </v-col>
                </v-row>


                <v-row v-if="extraFilters">
                    <v-col>
                        <span class="caption">{{ i18n.assignedUser_ }}</span>


                        <v-chip-group
                                column
                                multiple
                                v-model="q.assigned"
                        >
                            <v-chip :value="user.id" small label v-for="user in users" filter outlined>{{user.name}}</v-chip>
                        </v-chip-group>
                    </v-col>
                </v-row>

                <v-row v-if="extraFilters">
                    <v-col cols="12">
                        <span class="caption">{{ i18n.reviewer_ }}</span>

                        <v-chip-group
                                column
                                multiple
                                v-model="q.reviewer"
                        >
                            <v-chip label :value="user.id" small v-for="user in users" filter outlined>{{user.name}}</v-chip>
                        </v-chip-group>
                    </v-col>
                </v-row>


                <v-row v-if="extraFilters">
                    <v-col cols="12">
                        <span class="caption pt-2">{{ i18n.workflowStatus_ }}</span>


                        <v-chip-group
                                column
                                v-model="q.status"
                        >
                            <v-chip :value="status" label small v-for="status in statuses" filter outlined>{{status}}</v-chip>
                        </v-chip-group>

                    </v-col>
                </v-row>
               

                <v-row>
                    <v-col>
                        <div class="d-flex">
                            <search-field
                                    v-model="q.labels"
                                    api="/admin/api/labels/"
                                    query-params="&typ=for_indident&mode=2"
                                    item-text="title"
                                    item-value="id"
                                    :multiple="true"
                                    :label="i18n.includeLabels_"
                            ></search-field>
                            <v-checkbox :label="i18n.any_" dense v-model="q.oplabels" color="primary" small
                                        class="mx-3"></v-checkbox>
                        </div>

                        <search-field
                                v-model="q.exlabels"
                                api="/admin/api/labels/"
                                query-params="&typ=for_indident"
                                item-text="title"
                                item-value="id"
                                :multiple="true"
                                :label="i18n.excludeLabels_"
                        ></search-field>


                    </v-col>
                </v-row>
              

                <v-row>
                    <v-col>
                        <div class="d-flex">
                            <search-field
                                    v-model="q.locations"
                                    api="/admin/api/locations/"
                                    item-text="full_string"
                                    item-value="id"
                                    :multiple="true"
                                    :label="i18n.includeLocations_"
                            ></search-field>
                            <v-checkbox :label="i18n.any_" dense v-model="q.oplocations" color="primary" small
                                        class="mx-3"></v-checkbox>
                        </div>
                        <search-field
                                v-model="q.exlocations"
                                api="/admin/api/locations/"
                                item-text="full_string"
                                item-value="id"
                                :multiple="true"
                                :label="i18n.excludeLocations_"
                        ></search-field>


                    </v-col>
                </v-row>


                <v-row>
                    <v-col>
                        <search-field
                                v-model="q.elocation"
                                api="/admin/api/locations/"
                                item-text="full_string"
                                item-value="id"
                                :multiple="false"
                                :label="i18n.includeEventLocations_"
                        ></search-field>

                    </v-col>

                </v-row>


                <v-row>
                    <v-col cols="12" md="12">
                        <search-field
                                v-model="q.etype"
                                api="/admin/api/eventtypes/"
                                query-params="&typ=for_indident"
                                item-text="title"
                                item-value="id"
                                :multiple="false"
                                :label="i18n.eventType_"
                        ></search-field>

                    </v-col>

                </v-row>
                


            </v-container>

            <v-card-actions class="d-flex" style="position:sticky;padding:10px;background:white;bottom:0;">
                <v-spacer></v-spacer>
                <v-btn @click="q={}" text>{{ i18n.clearSearch_ }}</v-btn>

                <v-btn @click="$emit('search',q)" color="primary">{{ i18n.search_ }}</v-btn>
                <v-spacer></v-spacer>
            </v-card-actions>
        </v-card>

    `

})