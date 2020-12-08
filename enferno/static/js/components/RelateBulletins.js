Vue.component('relate-bulletins', {
    props: ['value', 'show', 'exid'],
    data: () => {
        return {
            q: {},
            loading: true,
            results: [],
            visible: false,
            page: 1,
            perPage: 10,
            total: 0,
            moreItems: false,
            bulletin: null,
            showBulletin: false,


        }

    }
    ,
    mounted() {

    },


    watch: {

        results: {
            handler(val, old) {

            },
            deep: true
        },

        value: function (val) {
            this.$emit('input', val);
        }
    },

    methods: {

        open() {
            this.visible = true;

        },
        close() {
            this.visible = false
        },
        reSearch() {
            this.page = 1;
            this.results = [];
            this.search();

        },

        search(q = {}) {
            this.loading = true;

            axios.post(`/admin/api/bulletins/?page=${this.page}&per_page=${this.perPage}&mode=2`, {q: [this.q]}).then(response => {
                this.loading = false
                this.exid = this.exid || -1;
                this.loading = false;
                this.total = response.data.total;

                this.results = this.results.concat(response.data.items.filter(x => x.id != this.exid));

                if (this.page * this.perPage >= this.total) {
                    this.moreItems = false;
                    console.log("Set more items");
                } else {
                    this.moreItems = true;
                }
            }).catch(err=>{
                console.log(err.response.data);
                this.loading = false;
            });


        },
        loadMore() {
            this.page += 1;
            this.search()
        },
        relateItem(item) {
            this.results.removeById(item.id);
            this.$emit('relate', item);

        }

    },


    template: `
        <v-dialog v-model="visible" max-width="1220">
            <v-sheet>

                <v-container class="fluid fill-height">
                    <v-row>
                        <v-col cols="12" md="4">
                            <v-card outlined>
                                <bulletin-search-box :i18n="$root.translations" v-model="q" :show-op="false"></bulletin-search-box>
                                <v-card-actions>
                                    <v-spacer></v-spacer>
                                    <v-btn color="primary" @click="reSearch">Search</v-btn>
                                    <v-spacer></v-spacer>
                                </v-card-actions>
                            </v-card>
                        </v-col>
                        <v-col cols="12" md="8"> 

                            <v-card :loading="loading">

                                <v-card-title class="handle">
                                    Advanced Search
                                    <v-spacer></v-spacer>
                                    <v-btn @click="visible=false" small text fab>
                                        <v-icon>mdi-close</v-icon>
                                    </v-btn>
                                </v-card-title>

                                <v-divider></v-divider>

                                <v-card-text v-if="loading" class="d-flex pa-5" justify-center align-center>
                                    <v-progress-circular class="ma-auto" indeterminate
                                                         color="primary"></v-progress-circular>
                                </v-card-text>


                                <v-card class="pa-2" tile color="grey lighten-4">

                                    <bulletin-result v-for="(item, i) in results" :key="i" :bulletin="item"
                                                     :show-hide="true">
                                        <template v-slot:actions>
                                            <v-btn @click="relateItem(item)" small depressed color="primary">relate
                                            </v-btn>
                                            
                                        </template>
                                    </bulletin-result>
                                </v-card>

                                <v-card-actions>
                                    <v-spacer></v-spacer>
                                    <v-btn icon @click="loadMore" v-if="moreItems" color="third">
                                        <v-icon>mdi-dots-horizontal</v-icon>
                                    </v-btn>
                                  <v-sheet small v-else class="heading" color=" grey--text">No (more) items found.</v-sheet>
                                    <v-spacer></v-spacer>
                                </v-card-actions>
                            </v-card>
                        </v-col>

                    </v-row>
                </v-container>

                <v-dialog v-model="showBulletin" max-width="550">
                    <v-sheet>
                        <div class="d-flex justify-end">
                            <v-btn @click="showBulletin=false" small text fab right="10">
                                <v-icon>mdi-close</v-icon>
                            </v-btn>
                        </div>
                        <bulletin-card :bulletin="bulletin"></bulletin-card>
                    </v-sheet>
                </v-dialog>


            </v-sheet>

        </v-dialog>

    `
})