<template lang="html">
    <div class="container">
        <div class="col-sm-12"><div class="row">

            <div class="panel panel-default">
                <div class="panel-heading">
                    <h3 class="panel-title">Park Entry Fees
                        <a :href="'#'+pBody" data-toggle="collapse"  data-parent="#userInfo" expanded="true" :aria-controls="pBody"></a>
                    </h3>
                </div>
                <div class="panel-body collapse in" :id="pBody">
                    <form method="post" name="new_payment" @submit.prevent="submit()" novalidate>
                        <input type="hidden" name="csrfmiddlewaretoken" :value="csrf_token"/>

                        <div id="error" v-if="errors.length > 0" style="margin: 10px; padding: 5px; color: red; border:1px solid red;">
                            <b>Please correct errors in row(s):</b>
                            <ul>
                                <li v-for="error in errors">
                                    {{error.name}}: {{ error.label }}
                                </li>
                            </ul>
                        </div>

                        <div id="id_warning" v-if="warnings.length > 0" style="margin: 10px; padding: 5px; color: blue; border:1px solid blue; display: none">
                            <div ref="warning" style="text-align:left;" :key="JSON.stringify(tbody)" :data="tbody">
                                <b>Multiple payment(s) selected:</b>
                                <ul>
                                    <li v-for="warning in warnings">
                                        {{warning.name}}: {{ warning.label }}
                                    </li>
                                </ul>
                            </div>
                        </div>


                        <label>Licence</label><v-select :options="licences" @change="proposal_parks()" v-model="selected_licence" :clearable="false"/>
                        <OrderTable ref="order_table" :expiry_date="selected_licence.expiry_date" :disabled="!parks_available" :headers="headers" :options="parks" name="payment" label="" id="id_payment" />

                        <div v-if="selected_licence.org_applicant==null">
                            <!-- Individual applicants must pay using Credit Card -->
                            <button :disabled="!parks_available" class="btn btn-primary pull-right" type="submit" style="margin-top:5px;">Proceed to Payment</button>
                        </div>
                        <div v-else class="dropdown" style="float: right;">
                            <button :disabled="!parks_available" class="btn btn-primary dropdown-toggle" type="button" id="dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false" name="payment_method" value="credit_card">
                                Proceed
                            </button>
                            <div class="dropdown-menu" aria-labelledby="dropdownMenuButton">
                                <button class="dropdown-item" type="submit">Pay by Credit Card</button><br>
                                <span v-if="selected_licence.bpay_allowed">
                                    <button class="dropdown-item" @click="payment_method='bpay'" type="submit">Pay by BPAY</button><br>
                                </span>
                                <span v-if="selected_licence.monthly_invoicing_allowed">
                                    <!--<button  class="dropdown-item" @click="submit_monthly_invoicing">Monthly Invoicing</button>-->
                                    <button type="submit" class="dropdown-item" @click="payment_method='monthly_invoicing'">Monthly Invoicing</button>
                                </span>
                                <span v-if="selected_licence.other_allowed">
                                   <button type="submit" class="dropdown-item" @click="payment_method='other'">Record Payment</button>
                                </span>
                            </div>
                        </div>

                        <button type="submit" class="dropdown-item" @click="payment_method='existing_invoice'">Existing invoice</button>

                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>

import OrderTable from './order_table.vue'
import Select from '@/components/forms/select.vue'
import {
    api_endpoints,
    helpers
}
from '@/utils/hooks'
    export default {
        name:'payment',
        components:{
            OrderTable,
            Select,
        },
        props:{
            proposal:{
                type: Object,
                required:true
            }
        },
        data:function () {
            let vm = this;
            return{
                values: null,
                headers: '{"Park": "select", "Arrival": "date", "Same tour group": "checkbox", "Passengers (6yrs+)": "number", "Children under 6 years": "number", "Free of charge":"number", "Cost":"total"}',
                parks: [],
                land_parks: [],
                parks_available: false,
                licences: [],
                errors: [],
                warnings: [],
                table_values: null,
                payment_method: null,
                selected_licence:{
                    default:function () {
                        return {
                            value: String,
                            label: String,
                            expiry_date: String,
                        }
                    }
                },
            }
        },
        computed: {
            _payment_url: function(){
                //return `/api/payment/${to.params.proposal_id}.json`;
                //return `/payment/${to.params.proposal_id}`;
                return `/payment/${this.proposal.id}`;
            },
            payment_url: function(){
                return '/payment/' + this.proposal.id + '/';
            },
            csrf_token: function() {
                return helpers.getCookie('csrftoken')
            },

            /*
            "type": "table",
            "headers": "{\"Species\": \"text\", \"Quantity\": \"number\", \"Date\": \"date\", \"Taken\": \"checkbox\"}",
            "name": "Section2-0",
            "label": "The first table in section 2"
            */
        },
        watch:{
            options: function(){
                if (!vm.parks_available) {
                    this.$refs.order_table.options.length = 0;
                    this.$refs.order_table.table_values.length = 0;
                }
            },
        },
        methods:{
            today: function() {
                var day = new Date();
                var dd = day.getDate();
                var mm = day.getMonth()+1; //January is 0!
                var yyyy = day.getFullYear();
                 if(dd<10){
                        dd='0'+dd
                    } 
                    if(mm<10){
                        mm='0'+mm
                    } 

                return new Date(yyyy+'-'+mm+'-'+dd);
            },

            resetTable: function(row) {
                /* Removes the rows, keeos the first and clears the td contents */
                let vm = this;
                //var nrows = $(".editable-table tbody tr").length;
                $(".editable-table tbody").find("tr:not(:first):not(:last)").remove(); // last row contains total price cell

                //vm.$refs.order_table.table.tbody = [["","","","","", ""]];
                //vm.$refs.order_table.table.tbody = [vm.$refs.order_table.init_row];
                vm.$refs.order_table.table.tbody = [vm.$refs.order_table.reset_row()];
                $(".editable-table .selected-tag").text('')
                $(".tbl_input").val('');
            },
            park_options: function() {
                let vm = this;
                vm.parks = [];
                for(var i = 0, length = vm.proposal.land_parks.length; i < length; i++) {
                    vm.parks.push({'label': vm.proposal.land_parks[i].park.name, 'value': vm.proposal.land_parks[i].park.id})
                }
            },
            calc_order: function(){
                let vm = this;
                var formData = new FormData(document.forms.new_payment);
                vm.order_details = formData.get('payment')
                vm.$refs.payment_calc.order_details = vm.order_details;
                vm.$refs.payment_calc.isModalOpen = true;
            },
            payment: function() {
                let vm = this;
                var proposal_id = vm.selected_licence.value;

                let formData = new FormData(vm.form);
                formData.append('tbody', JSON.stringify(vm.$refs.order_table.table.tbody))
                vm.$http.post(`/payment/${proposal_id}/`, formData,{
                    emulateJSON:true
                }).then((res) => {
                    swal(
                        'Payment',
                        'Your payment has been completed',
                        'success'
                    )
                },err=>{
                });
            },

            check_form_valid: function () {
                let vm = this;
                var idx_park = vm.$refs.order_table.idx_park;
                var idx_arrival_date = vm.$refs.order_table.idx_arrival_date;
                var idx_adult = vm.$refs.order_table.idx_adult;
                var idx_child = vm.$refs.order_table.idx_child;
                var idx_free = vm.$refs.order_table.idx_free;
                var idx_price = vm.$refs.order_table.idx_price;
                var idx_adult_same_tour = vm.$refs.order_table.idx_adult_same_tour;
                var idx_child_same_tour = vm.$refs.order_table.idx_child_same_tour;
                var idx_free_same_tour = vm.$refs.order_table.idx_free_same_tour;

                var errors = [];
                var tbody = vm.$refs.order_table.table.tbody;
                for (var row_idx in tbody) {
                    var row = tbody[row_idx];

                    if ( !(row[idx_park] || row[idx_arrival_date]) || !(row[idx_adult] || row[idx_child] || row[idx_free]) ) {
                        errors.push({id: parseInt(row_idx), name: "Row", label: parseInt(row_idx)+1})
                    }

                    var arrival_date = new Date(row[idx_arrival_date]);
                    if ( arrival_date < vm.today() ) {
                        errors.push({id: parseInt(row_idx), name: "Arrival Date", label: "Cannot be in the past" })
                    }

                    if ( arrival_date > new Date(vm.selected_licence.expiry_date) ) {
                        errors.push({id: parseInt(row_idx), name: "Arrival Date", label: "Cannot be beyond Licence expiry (Expiry:" +vm.selected_licence.expiry_date+ ")"})
                    }
                }

                return errors;
            },
            check_duplicate_parks: function () {
                /* https://stackoverflow.com/questions/53452875/find-if-two-arrays-are-repeated-in-array-and-then-select-them/53453045#53453045 */
                var t = {}
                var data = []
                var tbody = this.$refs.order_table.table.tbody;
                for (var i in tbody) {
                    // keep first 3 elements
                    var row = tbody[i];
                    //data.push(row.slice(0, 3))
                    data.push([row[0], row[1], row[2]=='' ? false:true])
                }
                //unique     = data.filter(( t={}, a=> !(t[a]=a in t) ));
                let duplicates = data.filter(( t={}, a=> (t[a]=a in t) ));
                return duplicates
            },
            duplicate_parks_str: function() {
                // <div ref="warning" style="text-align:left;"> <b>Multiple payment(s) selected:</b> <ul> <li v-for="warning in warnings"> {{warning.name}}: {{ warning.label }} </li> </ul> </div>
                var msg = '<div style=\"text-align:left;\"> <b>Multiple payment(s) selected:</b> <ul>'
                for (var i in this.warnings) {
                    console.log(this.warnings[i])
                    msg += '<li>' + this.warnings[i][0].label +': '+ this.warnings[i][1] + '</li>'
                }
                msg += '</ul> </div>'

                return msg
            },
            submit: function (e) {
                let vm = this;
                var form = document.forms.new_payment;
                if (vm.payment_method == 'existing_invoice') {
                    form.action = '/existing_invoice_payment/' + '05572566192'  + '/?method=' + vm.payment_method;
                    form.submit();
                }

                vm.errors = vm.check_form_valid();
                vm.warnings = vm.check_duplicate_parks()

                if (vm.warnings.length > 0) {
                    swal({
                        title: "Multiple park entry fee payments exist for the same date. Are you sure you want to continue?",
                        //html: vm.$refs.warning,
                        html: vm.duplicate_parks_str(),
                        type: "question",
                        showCancelButton: true,
                        confirmButtonText: 'Accept'

                    }).then(async (result) => {
                        if (result) {
                            if (vm.payment_method == 'monthly_invoicing' || vm.payment_method == 'bpay' || vm.payment_method == 'other') {
                                //form.action = '/payment_monthly/' + vm.selected_licence.value  + '/';
                                form.action = '/preview_deferred/' + vm.selected_licence.value  + '/?method=' + vm.payment_method;
                            } else {
                                form.action = '/payment/' + vm.selected_licence.value  + '/';
                            }
                            if (vm.errors.length == 0) {
                                form.submit();
                            } else {
                                return;
                            }
                        }
                    },(error) => {
                        //
                    });
                } else {
                    if (vm.payment_method == 'monthly_invoicing' || vm.payment_method == 'bpay' || vm.payment_method == 'other') {
                        //form.action = '/payment_monthly/' + vm.selected_licence.value  + '/';
                        form.action = '/preview_deferred/' + vm.selected_licence.value  + '/?method=' + vm.payment_method;
                    } else {
                        form.action = '/payment/' + vm.selected_licence.value  + '/';
                    }
                    if (vm.errors.length == 0) {
                        form.submit();
                    } else {
                        return;
                    }
                }
                
                this.warnings = [];

            },

            get_user_approvals: function(e) {
                let vm = this;
                vm.$http.get('/api/filtered_payments').then((res) => {
                    var licences = res.body;
                    for (var i in licences) {
                        vm.licences.push({
                            value:licences[i].current_proposal,
                            label:licences[i].lodgement_number,
                            expiry_date:licences[i].expiry_date,
                            org_applicant:licences[i].org_applicant,
                            bpay_allowed:licences[i].bpay_allowed,
                            monthly_invoicing_allowed:licences[i].monthly_invoicing_allowed,
                            other_allowed:licences[i].other_allowed,
                        });
                    }
                    console.log(vm.licences);
                },err=>{
                });
            },
            proposal_parks: function(e) {
                let vm = this;
                vm.$http.get(helpers.add_endpoint_json(api_endpoints.proposal_park,vm.selected_licence.value+'/proposal_parks')).then((res)=>{
                    vm.resetTable();
                    vm.land_parks = res.body.land_parks;
                    vm.parks = [];
                    for (var i in vm.land_parks) {
                        vm.parks.push({
                            value:vm.land_parks[i].park.id,
                            label:vm.land_parks[i].park.name,
                            prices:{
                                adult:vm.land_parks[i].park.adult_price,
                                child:vm.land_parks[i].park.child_price,
                                //senior:vm.land_parks[i].park.senior
                            },
                            region_id: vm.land_parks[i].park.region.id,
                            region_name: vm.land_parks[i].park.region.name,
                            max_group_arrival_by_date: vm.land_parks[i].park.max_group_arrival_by_date,
                        });
                    }
                    if (vm.parks.length==0) {
                        vm.parks_available = false;
                        vm.parks.push({value:0, label:'No parks available'});
                    } else{
                        vm.parks_available = true;
                    }
                    console.log(vm.land_parks);
                },err=>{
                });
            },
        },
        mounted:function () {
            let vm = this;
            vm.get_user_approvals();
        }
    }
</script>

<style lang="css" scoped>

.dropdown-item {
  border: 2px solid white;
  background-color: white;
  color: blue;
  padding: 10px 20px;
  font-size: 10;
  cursor: pointer;
  min-width: 180px;
}

</style>

