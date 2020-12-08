Vue.component("actor-result", {
    props: ['actor', 'hidden','showHide'],

    template: `
        <v-card outlined class="ma-2" v-if="!hidden">
            <v-card-title class="d-flex">
                <v-chip label small color="gv darken-2" dark>ID: {{actor.id}} </v-chip>
                <v-chip color="lime darken-3" class="white--text ml-1" label small># {{actor.originid}}</v-chip>
                <v-spacer></v-spacer>
                <v-chip v-if="actor.publish_date" small color="grey lighten-4">{{actor.publish_date}}</v-chip>
            </v-card-title>
            <slot name="header"></slot>
            <v-card-text>

                <div class="subtitle-2 black--text mb-1 mt-2">
                    {{actor.name}}
                </div>
                <div v-html="actor.description" class="caption">
                </div>
                <v-divider class="my-2"></v-divider>


                <div class="caption mt-2">Sources</div>
                <v-chip-group
                        column
                >
                    <v-chip small color="grey lighten-4" v-for="source in actor.sources" :key="source">
                        {{ source.title }}
                    </v-chip>
                </v-chip-group>

            </v-card-text>
            <v-card-actions>
                <slot name="actions"></slot>
                <v-btn v-if="showHide" @click="hidden=true" small depressed color="grey lighten-4">Hide</v-btn>
                <v-btn text small icon color="gv darken-1" @click.stop="$root.previewItem('/admin/api/actor/'+actor.id)"><v-icon>mdi-eye</v-icon></v-btn>
            </v-card-actions>
        </v-card>
    `
});
