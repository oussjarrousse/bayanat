Vue.component("actor-card", {
  props: ["actor", "close", "thumb-click", "active", "log", "diff","showEdit"],
  watch: {
    actor: function (b, n) {
      this.loadRevisions();
      if(!this.$root.currentUser.view_simple_history) {
        this.log = false;
      }
      if(this.$root.currentUser.view_full_history) {
        this.diff = true;
      }
    },
  },


  methods: {
    probability(item){
      return probs[item.probability]
    },
    actor_related_as(item) {
     if (this.actor.id < item.actor.id) {
       return actorConfig.atoaRelateAs[item.related_as].text;
     }else {
       return actorConfig.atoaRelateAs[item.related_as].revtext;
     }
    },
    bulletin_related_as(item) {
      return actorConfig.btoaRelateAs[item.related_as];

    },



     editAllowed(){
      return this.$root.editAllowed(this.actor) && this.showEdit;
    },
    removeVideo() {
      let video = this.$el.querySelector("#iplayer video");
      if (video) {
        video.remove();
      }
    },
    viewThumb(s3url) {

      this.$emit("thumb-click", s3url);
    },

    viewVideo(s3url) {
      this.removeVideo();

      let video = document.createElement("video");
      video.src = s3url;
      video.controls = true;
      video.autoplay = true;
      this.$el.querySelector("#iplayer").append(video);
    },

    loadRevisions() {
      axios.get(`/admin/api/actorhistory/${this.actor.id}`).then((response) => {
        this.revisions = response.data.items;
      });
    },

    showDiff(e, index) {
      this.diffDialog = true;
      //calculate diff
      const dp = jsondiffpatch.create({
        arrays: {
          detectMove: true,
        },
        objectHash: function (obj, index) {
          return obj.name || obj.id || obj._id || "$$index:" + index;
        },
      });

      const delta = dp.diff(
        this.revisions[index + 1].data,
        this.revisions[index].data
      );
      if (!delta) {
        this.diffResult = "Both items are Identical :)";
      } else {
        this.diffResult = jsondiffpatch.formatters.html.format(delta);
      }
    },
  },

  data: function () {
    return {
      diffResult: "",
      diffDialog: false,
      revisions: null,
      show: false,

      related_as: ['Same Person','Duplicate','Parent','Child','Sibling','Spouse','Family member','Superior officer','Subordinate officer','Subunit','Alleged Perpetrator','Member','Group','Unit','Other']
    };
  },

  template: `

    <v-card color="grey lighten-3"  class="mx-auto pa-3">
        <v-btn v-if="close" @click="$emit('close',$event.target.value)" fab absolute top right x-small text class="mt-6"><v-icon>mdi-close</v-icon></v-btn>
        <v-card-text class="d-flex align-center">
          <v-chip small pill label color="gv darken-2" class="white--text">
            ID {{actor.id}}</v-chip>
            
            <v-chip :href="actor.source_link" target="_blank"  small pill label color="lime darken-3 " class="white--text ml-1">
              # {{actor.originid}}</v-chip>
          <v-btn v-if="editAllowed()" class="ml-2" @click="$emit('edit',actor)" x-small outlined>Edit</v-btn>
        </v-card-text>

        
        <v-card-text>
          <h2 class="title black--text d-block">{{actor.name}} ({{actor.sex}})</h2>
        
          <div class="actor-description" v-html="actor.description"></div>
        </v-card-text>
            
        <uni-field caption="Full Name" :english="actor.name" :arabic="actor.name_ar" ></uni-field>
        <uni-field caption="Nickname" :english="actor.nickname" :arabic="actor.nickname_ar" ></uni-field>
        <div class="d-flex">
          <uni-field caption="First Name" :english="actor.first_name" :arabic="actor.first_name_ar" ></uni-field>
          <uni-field caption="Middle Name" :english="actor.middle_name" :arabic="actor.middle_name_ar" ></uni-field>
          
        </div>
        <uni-field caption="Last Name" :english="actor.last_name" :arabic="actor.last_name_ar" ></uni-field>
        <div class="d-flex">
          <uni-field caption="Mother's Name" :english="actor.mother_name" :arabic="actor.mother_name_ar" ></uni-field>
          <uni-field caption="Sex" :english="actor.sex"></uni-field>
          <uni-field caption="Age" :english="actor.age"></uni-field>
        </div>
        <div class="d-flex">
          <uni-field caption="Civilian" :english="actor.civilian"></uni-field>
          <uni-field caption="Actor Type" :english="actor.actor_type" ></uni-field>
          
        </div>
        <uni-field caption="Date of Birth" :english="actor.birth_date"></uni-field>
        <uni-field caption="Place of Birth" v-if="actor.birth_place" :english="actor.birth_place.full_string" ></uni-field>
        <uni-field caption="Place of Residence" v-if="actor.residence_place" :english="actor.residence_place.full_string"></uni-field>
        <uni-field caption="Place of Origin" v-if="actor.origin_place" :english="actor.origin_place.full_string"></uni-field>
        

        <div class="d-flex">
          <uni-field caption="Occupation" :english="actor.occupation" :arabic="actor.occupation_ar" ></uni-field>
          <uni-field caption="Position" :english="actor.position" :arabic="actor.position_ar" ></uni-field>
        </div>

        <div class="d-flex">
          <uni-field caption="Spoken Dialects" :english="actor.dialects" :arabic="actor.dialects_ar" ></uni-field>
          <uni-field caption="Family Status" :english="actor.family_status" :arabic="actor.family_status_ar" ></uni-field>
        </div>

        
               <v-card  v-if="actor.ethnography && actor.ethnography.length" outlined class="mx-2 my-1 pa-2 d-flex align-center flex-grow-1" color="grey lighten-5 " > 
                 <div class="caption grey--text mr-2">Ethnographic Info</div>
                       <v-chip x-small v-for="e in actor.ethnography" class="caption black--text mx-1">{{e}}</v-chip>

               </v-card>
              <v-card  v-if="actor.nationality && actor.nationality.length" outlined class="mx-2 my-1 pa-2 d-flex align-center flex-grow-1" color="grey lighten-5 " > 
                 <div class="caption grey--text mr-2">Nationalities</div>
                       <v-chip x-small v-for="n in actor.nationality" class="caption black--text mx-1">{{n}}</v-chip>

               </v-card>
        
        
        <uni-field caption="National ID Card" :english="actor.national_id_card" ></uni-field>

  <v-card outlined class="ma-3" color="grey lighten-5"> 
              <v-card-text>
                <div class="px-1 title black--text">Overview</div>
                <v-chip v-if="actor.civilian" class="grey lighten-4 ma-1" small>{{actor.civilian}}</v-chip>
                <v-chip v-if="actor.actor_type" class="grey lighten-4 ma-1" small>{{actor.actor_type}}</v-chip>
                <v-chip v-if="actor.birth_place" class="grey lighten-4 ma-1" small>Born in {{actor.birth_place.full_string}} </v-chip>
                <v-chip v-if="actor.residence_place" class="grey lighten-4 ma-1" small>Resides in {{actor.residence_place.full_string}} </v-chip>
                </v-card-text>
</v-card>
        

      
        

        
        <v-card outlined class="ma-3" color="grey lighten-5" v-if="actor.sources && actor.sources.length" > 
          
                <v-card-text>
                  <div class="px-1 title black--text">Sources</div>
          <v-chip-group  column>
            <v-chip small color="blue-grey lighten-5"  v-for="source in actor.sources" :key="source.id">{{source.title}}</v-chip>
          </v-chip-group>
        </v-card-text>
        </v-card>
        
        
        <v-card outlined class="ma-3" color="grey lighten-5" v-if="actor.labels && actor.labels.length" >
            <v-card-text>
              <div class="px-1 title black--text">Labels</div>
          <v-chip-group column>
            <v-chip small color="blue-grey lighten-5" v-for="label in actor.labels" :key="label.id">{{label.title}}</v-chip>
          </v-chip-group>
        </v-card-text>
        </v-card>
      
      <v-card outlined class="ma-3" color="grey lighten-5" v-if="actor.verLabels && actor.verLabels.length" >
            <v-card-text>
              <div class="px-1 title black--text">Verified Labels</div>
          <v-chip-group column>
            <v-chip small color="blue-grey lighten-5" v-for="label in actor.verLabels" :key="label.id">{{label.title}}</v-chip>
          </v-chip-group>
        </v-card-text>
        </v-card>

        
       


        <v-card outlined class="ma-2" color="grey lighten-5" v-if="actor.events && actor.events.length" >
          <v-card-text class="pa-2">
            <div class="px-1 title black--text">Events</div>
          <event-card  v-for="event in actor.events" :key="event.id" :event="event"></event-card>
           </v-card-text>
        </v-card>

        

      <v-card outlined class="ma-3" v-if="actor.medias && actor.medias.length" >
        <v-card outlined id="iplayer" v-if="active">
        
        </v-card>
        <v-card-text>
          <div class="px-1 mb-3 title black--text">Media</div>   
          <v-layout wrap>
            <v-flex class="ma-2"  md6 v-for="media in actor.medias" >
              <media-card v-if="active" @thumb-click="viewThumb" @video-click="viewVideo"  :media="media" ></media-card>  
              </v-flex>
          </v-layout>
        </v-card-text>
     </v-card>


      <v-card outlined class="ma-3" v-if="actor.actor_relations && actor.actor_relations.length" >
          
          <v-card-text>
            <div class="px-1 title black--text">Related Actors</div>
              <actor-result class="mt-1" v-for="(item,index) in actor.actor_relations" :key="index" :actor="item.actor">
                <template v-slot:header>

                  <v-sheet color="yellow lighten-5" class="pa-2">

                    <div class="caption ma-2">Relationship Info</div>
                    <v-chip color="grey lighten-4" small label>{{probability(item)}}</v-chip>
                    <v-chip v-if="item.related_as!=null" color="grey lighten-4" small label>{{actor_related_as(item)}}</v-chip>
                    <v-chip color="grey lighten-4" small label>{{item.comment}}</v-chip>

                  </v-sheet>

                </template>
              </actor-result>
          </v-card-text>
      </v-card>

      <v-card outlined class="ma-3" v-if="actor.bulletin_relations && actor.bulletin_relations.length" >
          
        <v-card-text>
          <div class="px-1 title black--text">Related Bulletins</div>
            <bulletin-result class="mt-1" v-for="(item,index) in actor.bulletin_relations" :key="index" :bulletin="item.bulletin">
              <template v-slot:header>
                              <v-sheet color="yellow lighten-5" class="pa-2">
                                <div class="caption ma-2">Relationship Info</div>
                              <v-chip color="grey lighten-4" small label>{{probability(item)}}</v-chip>  
                              <v-chip color="grey lighten-4" small label>{{bulletin_related_as(item)}}</v-chip>  
                              <v-chip color="grey lighten-4" small label>{{item.comment}}</v-chip>  
                                
                              </v-sheet>
                              
                            </template>
            </bulletin-result>
        </v-card-text>
      </v-card>


      <v-card outlined class="ma-3" v-if="actor.incident_relations && actor.incident_relations.length" >
      <v-card-text>
        <div class="px-1 title black--text">Related Incidents</div>
          <incident-result class="mt-1" v-for="(item,index) in actor.incident_relations" :key="index" :incident="item.incident">
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



   
      <div class="d-flex">
        <uni-field caption="Publish Date" :english="actor.publish_date"></uni-field>
        <uni-field caption="Documentation Date" :english="actor.documentation_date"></uni-field>
      </div>
      <uni-field caption="Source Link" :english="actor.source_link"></uni-field>

      
      
      <v-card v-if="actor.review"  outline elevation="0" class="ma-3" color="light-green lighten-5" >
        <v-card-text>
        <div class="px-1 title black--text">Review</div>
        <div v-html="actor.review" class="pa-1 my-2 grey--text text--darken-2">
          
        </div>
        <v-chip small label  color="lime" >{{actor.review_action}}</v-chip>
      </v-card-text>
      </v-card>

      

    <v-card v-if="log" outline elevation="0" color="ma-3" >
      <v-card-text>
      <h3 class="title black--text">Log History</h3>
      
        <template v-for="(revision,index) in revisions">
        <v-sheet color="grey lighten-4" dense flat class="my-1 pa-2 d-flex align-center" >
          <span class="caption">{{revision.data['comments']}} - <v-chip x-small label color="gv lighten-3">{{revision.data.status}}</v-chip> - {{revision.created_at}} - By {{revision.user.email}}</span>
<v-spacer></v-spacer>

<v-btn v-if="diff" v-show="index!=revisions.length-1" @click="showDiff($event,index)" class="mx-1" color="grey" icon small><v-icon>mdi-compare</v-icon></v-btn>

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
      `,
});
