<template>
    <!-- <div v-if="email_user" class="card"> -->
    <div id="organisationLinkedUser" class="container">
        <teleport to="#organisation-privacy-notice-target">
            <PrivacyNotice />
        </teleport>

        <teleport to="#organisation-comms-teleport-target">
            <h3 v-if="organisationCommsHeading" class="mb-3">
                {{ organisationCommsHeading }}
            </h3>
            <CommsLogs
                :comms_url="comms_url"
                :logs_url="logs_url"
                :comms_add_url="comms_add_url"
                :disable_add_entry="false"
            />
        </teleport>

        <teleport to="#contacts-teleport-target">
            <FormSection
                :form-collapse="false"
                label="Contact Details"
                index="contact_details"
            >
                <div v-if="isContactDetailsLoading" class="py-3">
                    <div
                        class="d-flex justify-content-center align-items-center mt-2"
                    >
                        <div class="spinner-grow text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                    </div>
                    <div
                        class="d-flex justify-content-center align-items-center mt-2"
                    >
                        <strong>Loading</strong>
                    </div>
                </div>
                <div v-show="!isContactDetailsLoading">
                    <datatable
                        v-if="isContactDetailsTableReady"
                        id="organisation_contact_details_datatable_ref"
                        ref="contacts_datatable_details"
                        :dt-options="contact_details_options_ref"
                        :dt-headers="contact_details_headers_ref"
                    />
                </div>
            </FormSection>

            <modal
                transition="modal fade"
                title="Update Contact"
                large
                @ok="submitContactEdit"
                @cancel="close"
            >
                <div class="container-fluid">
                    <div class="row">
                        <form
                            class="form-horizontal"
                            @submit.prevent="submitContactEdit"
                        >
                            <div class="form-group row mb-3">
                                <label class="col-sm-3 col-form-label"
                                    >Given Name(s):</label
                                >
                                <div class="col-sm-9">
                                    <input
                                        v-model="editContact.first_name"
                                        type="text"
                                        class="form-control"
                                        required
                                        disabled
                                    />
                                </div>
                            </div>

                            <div class="form-group row mb-3">
                                <label class="col-sm-3 col-form-label"
                                    >Surname:</label
                                >
                                <div class="col-sm-9">
                                    <input
                                        v-model="editContact.last_name"
                                        type="text"
                                        class="form-control"
                                        required
                                        disabled
                                    />
                                </div>
                            </div>

                            <div class="form-group row mb-3">
                                <label class="col-sm-3 col-form-label"
                                    >Phone:</label
                                >
                                <div class="col-sm-9">
                                    <input
                                        v-model="editContact.phone_number"
                                        type="text"
                                        class="form-control"
                                    />
                                </div>
                            </div>

                            <div class="form-group row mb-3">
                                <label class="col-sm-3 col-form-label"
                                    >Mobile:</label
                                >
                                <div class="col-sm-9">
                                    <input
                                        v-model="editContact.mobile_number"
                                        type="text"
                                        class="form-control"
                                    />
                                </div>
                            </div>

                            <div class="form-group row mb-3">
                                <label class="col-sm-3 col-form-label"
                                    >Fax:</label
                                >
                                <div class="col-sm-9">
                                    <input
                                        v-model="editContact.fax_number"
                                        type="text"
                                        class="form-control"
                                    />
                                </div>
                            </div>

                            <div class="form-group row mb-3">
                                <label class="col-sm-3 col-form-label"
                                    >Email:</label
                                >
                                <div class="col-sm-9">
                                    <input
                                        v-model="editContact.email"
                                        type="email"
                                        class="form-control"
                                        required
                                        disabled
                                    />
                                </div>
                            </div>
                        </form>
                    </div>
                </div>
                <template #footer>
                    <button
                        type="button"
                        class="btn btn-primary"
                        @click="submitContactEdit"
                    >
                        Ok
                    </button>
                    <button
                        type="button"
                        class="btn btn-secondary"
                        @click="close"
                    >
                        Cancel
                    </button>
                </template>
            </modal>
        </teleport>

        <teleport to="#linkedusers-teleport-target">
            <FormSection
                :form-collapse="false"
                label="Linked User Accounts"
                index="linked_user_accounts"
                subtitle="Manage the user accounts linked to the organisation"
            >
                <div v-if="isLinkedUsersLoading" class="py-3">
                    <div
                        class="d-flex justify-content-center align-items-center mt-2"
                    >
                        <div class="spinner-grow text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                    </div>
                    <div
                        class="d-flex justify-content-center align-items-center mt-2"
                    >
                        <strong>Loading</strong>
                    </div>
                </div>
                <div v-show="!isLinkedUsersLoading">
                    <div class="row">
                        <div class="col-sm-12">
                            <div v-if="org" class="row mb-3">
                                <div class="col-sm-12">
                                    <h4>
                                        Persons linked to this organisation:
                                    </h4>
                                </div>
                                <div v-for="d in org.delegates" :key="d.id">
                                    <div v-if="d.is_admin" class="row mb-1">
                                        <label
                                            :for="`organisation_admin_${d.id}`"
                                            class="col-sm-3"
                                        >
                                            <i
                                                class="bi bi-shield-lock-fill"
                                                style="color: #007bff"
                                            ></i
                                            >&nbsp;
                                            <strong>Organisation Admin:</strong>
                                        </label>
                                        <div class="col-sm-9">
                                            <input
                                                class="form-control w-100"
                                                type="text"
                                                :value="`${d.name} (${d.email})`"
                                                aria-label="organisation admin name"
                                                :name="`organisation_admin_${d.id}`"
                                                disabled
                                                readonly
                                            />
                                        </div>
                                    </div>
                                    <div v-else class="row mb-1">
                                        <label
                                            :for="`organisation_user_${d.id}`"
                                            class="col-sm-3"
                                        >
                                            <i
                                                class="bi bi-person-fill"
                                                style="color: #007bff"
                                            ></i
                                            >&nbsp;
                                            <strong>Organisation User:</strong>
                                        </label>
                                        <div class="col-sm-9">
                                            <input
                                                class="form-control w-100"
                                                type="text"
                                                :value="`${d.name} (${d.email})`"
                                                aria-label="organisation user name"
                                                :name="`organisation_user_${d.id}`"
                                                disabled
                                                readonly
                                            />
                                        </div>
                                    </div>
                                </div>
                                <div class="col-sm-12 top-buffer-s mb-3 mt-3">
                                    <alert
                                        type="info"
                                        icon="info-circle"
                                        class="alert alert-info"
                                    >
                                        <i
                                            class="bi bi-exclamation-triangle-fill"
                                            style="color: #dc3545"
                                        ></i
                                        >&nbsp; The Department cannot manage
                                        this list of people. The organisation is
                                        responsible for managing people linked
                                        to the organisation.
                                        <br />
                                    </alert>
                                </div>
                            </div>
                        </div>
                    </div>

                    <form
                        v-if="org?.pins"
                        class="form-horizontal"
                        action="index.html"
                        method="post"
                    >
                        <div class="row mb-2">
                            <label
                                for=""
                                class="col-sm-3 control-label fw-bold"
                            >
                                User Pin Code 1:</label
                            >
                            <span class="col-sm-3 fw-light">
                                {{ org.pins.three }}
                            </span>
                            <label
                                for=""
                                class="col-sm-3 control-label fw-bold"
                            >
                                User Pin Code 2:</label
                            >
                            <div class="col-sm-3 fw-light">
                                {{ org.pins.four }}
                            </div>
                        </div>
                        <div class="row mb-3">
                            <label
                                for=""
                                class="col-sm-3 control-label fw-bold"
                            >
                                Admin Pin Code 1:</label
                            >
                            <span class="col-sm-3 fw-light">
                                {{ org.pins.one }}
                            </span>
                            <label
                                for=""
                                class="col-sm-3 control-label fw-bold"
                            >
                                Admin Pin Code 2:</label
                            >
                            <div class="col-sm-3 fw-light">
                                {{ org.pins.two }}
                            </div>
                        </div>
                    </form>
                    <div>
                        <datatable
                            id="organisation_contacts_datatable_ref"
                            ref="contacts_datatable_user"
                            v-model="filterOrgContactStatus"
                            :dt-options="contacts_options_ref"
                            :dt-headers="contacts_headers_ref"
                        />
                    </div>
                </div>
            </FormSection>

            <AddCommLog
                v-if="showAddCommsModal"
                ref="add_comm_org_user_action"
                :url="comms_add_url"
                :action="pendingCommsAction"
                @refreshActionFromResponse="handleCommsActionFromCommsLog"
            />
        </teleport>
    </div>
</template>

<script>
import { api_endpoints, constants, helpers, utils } from '@/utils/hooks';
import alert from '@vue-utils/alert.vue';
import datatable from '@vue-utils/datatable.vue';
import AddCommLog from '@common-utils/add_comm_log_org.vue';
import CommsLogs from '@common-utils/comms_logs.vue';
import PrivacyNotice from '@common-utils/privacy_notice.vue';
import FormSection from '@/components/forms/section_toggle.vue';
import modal from '@vue-utils/bootstrap-modal.vue';
import $ from 'jquery';
export default {
    name: 'OrganisationComponent',
    components: {
        alert,
        datatable,
        AddCommLog,
        CommsLogs,
        PrivacyNotice,
        FormSection,
        modal,
    },
    data() {
        const vm = this;
        return {
            api_endpoints: api_endpoints,
            comms_url: helpers.add_endpoint_json(
                api_endpoints.organisations,
                vm.$route.params.org_id + '/comms_log'
            ),
            logs_url: helpers.add_endpoint_json(
                api_endpoints.organisations,
                vm.$route.params.org_id + '/action_log'
            ),
            comms_add_url: helpers.add_endpoint_json(
                api_endpoints.organisations,
                vm.$route.params.org_id + '/add_comms_log'
            ),
            email_user: null,
            selectedOrganisation: null,
            newOrganisation: null,
            organisation_requests: null,
            validatePinsError: null,
            validatingPins: false,
            pins: {
                pin1: '',
                pin2: '',
            },
            helpers: helpers,
            org: null,
            is_org_admin: false,
            contact_details_headers_ref: [
                'Name',
                'Phone',
                'Mobile',
                'Fax',
                'Email',
                'Action',
            ],
            contact_details_options_ref: {
                language: {
                    processing: constants.DATATABLE_PROCESSING_HTML,
                },
                responsive: true,
                ajax: {
                    url: helpers.add_endpoint_json(
                        api_endpoints.organisations,
                        vm.$route.params.org_id + '/contacts_exclude'
                    ),
                    dataSrc: '',
                },
                columns: [
                    {
                        data: 'id',
                        mRender: function (data, type, full) {
                            return `${full.first_name || ''} ${full.last_name || ''}`.trim();
                        },
                    },
                    { data: 'phone_number' },
                    { data: 'mobile_number' },
                    { data: 'fax_number' },
                    { data: 'email' },
                    {
                        data: 'id',
                        mRender: function (data, type, full) {
                            if (
                                vm.is_commercialoperator_admin ||
                                vm.is_org_admin ||
                                vm.is_org_access_member
                            ) {
                                return `<a href='#' class='edit_contact' data-id='${full.id}' data-firstname='${full.first_name || ''}' data-lastname='${full.last_name || ''}' data-phone='${full.phone_number || ''}' data-mobile='${full.mobile_number || ''}' data-fax='${full.fax_number || ''}' data-email='${full.email || ''}'>Edit</a>`;
                            }
                            return '';
                        },
                    },
                ],
                processing: true,
            },
            contacts_headers_ref: ['Name', 'Role', 'Email', 'Status', 'Action'],
            contacts_options_ref: {
                language: {
                    processing: constants.DATATABLE_PROCESSING_HTML,
                },
                responsive: true,
                ajax: {
                    url: helpers.add_endpoint_json(
                        api_endpoints.organisations,
                        vm.$route.params.org_id + '/contacts_exclude'
                    ),

                    dataSrc: '',
                },
                columns: [
                    {
                        data: 'id',
                        mRender: function (data, type, full) {
                            return full.first_name + ' ' + full.last_name;
                        },
                    },
                    {
                        data: 'user_role',
                        mRender: function (data, type, full) {
                            if (full.user_role == 'Organisation Admin') {
                                return `<i class='bi bi-shield-lock-fill' style='color: #007bff' ></i>&nbsp;${full.user_role}`;
                            } else if (full.user_role == 'Organisation User') {
                                return `<i class='bi bi-person-fill' style='color: #007bff' ></i>&nbsp;${full.user_role}`;
                            } else {
                                return full.user_role;
                            }
                        },
                    },
                    { data: 'email' },
                    {
                        data: 'user_status',
                        mRender: function (data, type, full) {
                            let links = '';
                            if (full.user_status == 'Pending') {
                                links += `<span class='badge bg-warning me-1 p-2'>${full.user_status}</span>`;
                            } else if (full.user_status == 'Active') {
                                links += `<span class='badge bg-success me-1 p-2'><i class="fas fa-link"></i> ${full.user_status}</span>`;
                            } else if (full.user_status == 'Declined') {
                                links += `<span class='badge bg-danger me-1 p-2'>${full.user_status}</span>`;
                            } else if (full.user_status == 'Suspended') {
                                links += `<span class='badge bg-danger me-1 p-2'>${full.user_status}</span>`;
                            } else if (full.user_status == 'Unlinked') {
                                links += `<span class='badge bg-secondary me-1 p-2'><i class="fas fa-link-slash"></i> ${full.user_status}</span>`;
                            } else if (full.user_status == 'ContactForm') {
                                links += `<span class='badge bg-info me-1 p-2'>${full.user_status}</span>`;
                            } else {
                                links += `<span class='badge bg-secondary me-1 p-2'>${full.user_status}</span>`;
                            }
                            return links;
                        },
                    },
                    {
                        data: 'id',
                        mRender: function (data, type, full) {
                            let links = '';
                            if (
                                vm.is_commercialoperator_admin ||
                                vm.is_org_admin
                            ) {
                                if (full.user_status == 'Pending') {
                                    links += `<a data-email='${full.email}' data-firstname='${full.first_name}' data-lastname='${full.last_name}' data-id='${full.id}' data-mobile='${full.mobile_number}' data-phone='${full.phone_number}' class="accept_contact">Accept</a><br/>`;
                                    links += `<a data-email='${full.email}'  data-firstname='${full.first_name}' data-lastname='${full.last_name}' data-id='${full.id}' data-mobile='${full.mobile_number}' data-phone='${full.phone_number}' class="decline_contact">Decline</a><br/>`;
                                } else if (full.user_status == 'Suspended') {
                                    links += `<a data-email='${full.email}' data-firstname='${full.first_name}' data-lastname='${full.last_name}' data-id='${full.id}' data-mobile='${full.mobile_number}' data-phone='${full.phone_number}' class="reinstate_contact">Reinstate</a><br/>`;
                                } else if (full.user_status == 'Active') {
                                    links += `<button class='btn btn-danger btn-sm btn-status unlink_contact' role='button' data-email='${full.email}' data-firstname='${full.first_name}' data-lastname='${full.last_name}' data-id='${full.id}' data-mobile='${full.mobile_number}' data-phone='${full.phone_number}'><i class="fas fa-link-slash"></i> Unlink</button><br/>`;
                                    links += `<a data-email='${full.email}'  data-firstname='${full.first_name}' data-lastname='${full.last_name}' data-id='${full.id}' data-mobile='${full.mobile_number}' data-phone='${full.phone_number}' class="suspend_contact">Suspend</a><br/>`;
                                    if (full.user_role == 'Organisation User') {
                                        links += `<a data-email='${full.email}'  data-firstname='${full.first_name}' data-lastname='${full.last_name}' data-id='${full.id}' data-mobile='${full.mobile_number}' data-phone='${full.phone_number}' class="make_admin_contact">Make Organisation Admin</a><br/>`;
                                    } else {
                                        links += `<a data-email='${full.email}'  data-firstname='${full.first_name}' data-lastname='${full.last_name}' data-id='${full.id}' data-mobile='${full.mobile_number}' data-phone='${full.phone_number}' class="make_user_contact">Make Organisation User</a><br/>`;
                                    }
                                } else if (full.user_status == 'Unlinked') {
                                    links += `<a data-email='${full.email}'  data-firstname='${full.first_name}' data-lastname='${full.last_name}' data-id='${full.id}' data-mobile='${full.mobile_number}' data-phone='${full.phone_number}' class="relink_contact">Reinstate</a><br/>`;
                                } else if (full.user_status == 'Declined') {
                                    links += `<a data-email='${full.email}'  data-firstname='${full.first_name}' data-lastname='${full.last_name}' data-id='${full.id}' data-mobile='${full.mobile_number}' data-phone='${full.phone_number}' class="accept_declined_contact">Accept (Previously Declined)</a><br/>`;
                                }
                            }
                            return links;
                        },
                    },
                ],
                processing: true,
            },
            filterOrgContactStatus: null,
            is_commercialoperator_admin: false,
            is_org_access_member: false,
            contact_user: {
                first_name: null,
                last_name: null,
                email: null,
                mobile_number: null,
                phone_number: null,
            },
            isContactDetailsLoading: true,
            isLinkedUsersLoading: true,
            user_action: 'unlink',
            isContactDetailsTableReady: false,
            isModalOpen: false,
            showAddCommsModal: false,
            pendingCommsAction: '',
            editContact: {
                id: null,
                first_name: '',
                last_name: '',
                phone_number: '',
                mobile_number: '',
                fax_number: '',
                email: '',
            },
        };
    },
    computed: {
        organisationCommsHeading: function () {
            const orgName = this.org?.name || this.org?.organisation_name || '';
            const orgAbn = this.org?.abn || this.org?.organisation_abn || '';

            if (orgName && orgAbn) {
                return `${orgName} - ${orgAbn}`;
            }
            return orgName || orgAbn || '';
        },
        linkOrganisationTitle: function () {
            if (
                this.organisation_requests &&
                this.organisation_requests.length
            ) {
                return 'Link another Organisation';
            }
            return 'Link an organisation';
        },
        csrf_token: function () {
            return helpers.getCookie('csrftoken');
        },
    },
    created: function () {
        console.log('organisation.vue created');
        this.$nextTick(() => {
            window.requestAnimationFrame(() => {
                this.fetchInitialData().then((response) => {
                    console.log('fetch initial data', response);
                });
            });
        });
    },
    mounted: function () {
        console.log('organisation.vue mounted');
        this.$nextTick(() => {
            this.initialiseSectionLoaders();
            if (this.$refs.contacts_datatable_user) {
                this.eventListeners();
            }
        });
    },
    methods: {
        close: function () {
            this.isModalOpen = false;
        },
        bindContactDetailsEditListener: function () {
            const vm = this;
            vm.$refs.contacts_datatable_details.vmDataTable.on(
                'click',
                '.edit_contact',
                function (e) {
                    e.preventDefault();
                    const rowData = {
                        id: $(this).data('id'),
                        first_name: $(this).data('firstname') || '',
                        last_name: $(this).data('lastname') || '',
                        phone_number: $(this).data('phone') || '',
                        mobile_number: $(this).data('mobile') || '',
                        fax_number: $(this).data('fax') || '',
                        email: $(this).data('email') || '',
                    };

                    vm.editContact = { ...rowData };
                    vm.isModalOpen = true;
                }
            );
        },
        submitContactEdit: function () {
            const vm = this;
            helpers
                .fetchUrl(
                    helpers.add_endpoint_json(
                        api_endpoints.organisations,
                        vm.org.id + '/update_contact'
                    ),
                    {
                        method: 'POST',
                        body: JSON.stringify(vm.editContact),
                        headers: {
                            'Content-Type': 'application/json',
                        },
                    }
                )
                .then(
                    () => {
                        vm.close();
                        vm.$refs.contacts_datatable_details.vmDataTable.ajax.reload();
                        vm.$refs.contacts_datatable_user.vmDataTable.ajax.reload();
                        swal.fire({
                            title: 'Update Contact',
                            text: 'Contact details were updated successfully.',
                            icon: 'success',
                            confirmButtonText: 'OK',
                        });
                    },
                    (error) => {
                        swal.fire({
                            title: 'Update Contact',
                            text: helpers.apiVueResourceError(error),
                            icon: 'error',
                        });
                    }
                );
        },
        initialiseSectionLoaders: function () {
            const vm = this;

            if (
                vm.isContactDetailsTableReady &&
                vm.$refs.contacts_datatable_details?.vmDataTable
            ) {
                vm.$refs.contacts_datatable_details.vmDataTable.one(
                    'xhr',
                    function () {
                        vm.isContactDetailsLoading = false;
                    }
                );
            } else if (vm.isContactDetailsTableReady) {
                vm.isContactDetailsLoading = false;
            }

            if (vm.$refs.contacts_datatable_user?.vmDataTable) {
                vm.$refs.contacts_datatable_user.vmDataTable.one(
                    'xhr',
                    function () {
                        vm.isLinkedUsersLoading = false;
                    }
                );
            } else {
                vm.isLinkedUsersLoading = false;
            }
        },
        orgAction: function (action) {
            let vm = this;
            const name =
                `${vm.contact_user.first_name || ''} ${vm.contact_user.last_name || ''}`.trim();
            const displayName = name || vm.contact_user.email || 'this user';
            if (action) {
                if (action == 'unlink') {
                    helpers
                        .fetchUrl(
                            helpers.add_endpoint_json(
                                api_endpoints.organisations,
                                vm.org.id + '/unlink_user'
                            ),
                            {
                                method: 'POST',
                                body: JSON.stringify(vm.contact_user),
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                            }
                        )
                        .then(
                            () => {
                                // Note: This block is missing a response to retrieve the name from
                                swal.fire({
                                    title: 'Unlink',
                                    text:
                                        'You have successfully unlinked ' +
                                        displayName +
                                        '.',
                                    icon: 'success',
                                    confirmButtonText: 'OK',
                                }).then(
                                    () => {
                                        vm.$refs.contacts_datatable_user.vmDataTable.ajax.reload();
                                        if (
                                            vm.contact_user.email ==
                                            vm.profile.email
                                        ) {
                                            this.$router.push('/external');
                                        }
                                    },
                                    () => {}
                                );
                            },
                            (error) => {
                                if (error.status == 500) {
                                    swal.fire({
                                        title: 'Unlink',
                                        text: 'Last Organisation Admin can not be unlinked.',
                                        icon: 'error',
                                    });
                                } else {
                                    swal.fire({
                                        title: 'Unlink',
                                        text:
                                            'There was an error unlinking ' +
                                            displayName +
                                            '. ' +
                                            helpers.apiVueResourceError(error),
                                        icon: 'error',
                                    });
                                }
                            }
                        );
                } else if (action == 'relink') {
                    helpers
                        .fetchUrl(
                            helpers.add_endpoint_json(
                                api_endpoints.organisations,
                                vm.org.id + '/relink_user'
                            ),
                            {
                                method: 'POST',
                                body: JSON.stringify(vm.contact_user),
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                            }
                        )
                        .then(
                            () => {
                                // Note: This block is missing a response to retrieve the name from
                                swal.fire({
                                    title: 'Relink User',
                                    text:
                                        'You have successfully relinked ' +
                                        displayName +
                                        '.',
                                    icon: 'success',
                                    confirmButtonText: 'OK',
                                }).then(
                                    () => {
                                        vm.$refs.contacts_datatable_user.vmDataTable.ajax.reload();
                                    },
                                    () => {}
                                );
                            },
                            (error) => {
                                // Note: The alert text seems to indicate to display the user name, but the name is not retrieved from the error response
                                swal.fire({
                                    title: 'Relink User',
                                    text:
                                        'There was an error relinking ' +
                                        displayName +
                                        '. ' +
                                        helpers.apiVueResourceError(error),
                                    icon: 'error',
                                });
                            }
                        );
                } else if (action == 'suspend') {
                    helpers
                        .fetchUrl(
                            helpers.add_endpoint_json(
                                api_endpoints.organisations,
                                vm.org.id + '/suspend_user'
                            ),
                            {
                                method: 'POST',
                                body: JSON.stringify(vm.contact_user),
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                            }
                        )
                        .then(
                            () => {
                                // Note: This block is missing a response to retrieve the name from
                                swal.fire({
                                    title: 'Suspend User',
                                    text:
                                        'You have successfully suspended ' +
                                        displayName +
                                        ' as a User.',
                                    icon: 'success',
                                    confirmButtonText: 'OK',
                                }).then(
                                    () => {
                                        vm.$refs.contacts_datatable_user.vmDataTable.ajax.reload();
                                        if (
                                            vm.contact_user.email ==
                                            vm.profile.email
                                        ) {
                                            this.$router.push('/external');
                                        }
                                    },
                                    () => {}
                                );
                            },
                            (error) => {
                                // Note: The alert text seems to indicate to display the user name, but the name is not retrieved from the error response
                                swal.fire({
                                    title: 'Suspend User',
                                    text:
                                        'There was an error suspending ' +
                                        displayName +
                                        ' as a User.',
                                    icon: 'error',
                                });
                            }
                        );
                } else if (action == 'reinstate') {
                    helpers
                        .fetchUrl(
                            helpers.add_endpoint_json(
                                api_endpoints.organisations,
                                vm.org.id + '/reinstate_user'
                            ),
                            {
                                method: 'POST',
                                body: JSON.stringify(vm.contact_user),
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                            }
                        )
                        .then(
                            () => {
                                // Note: This block is missing a response to retrieve the name from
                                swal.fire({
                                    title: 'Reinstate User',
                                    text:
                                        'You have successfully reinstated ' +
                                        displayName +
                                        '.',
                                    icon: 'success',
                                    confirmButtonText: 'OK',
                                }).then(
                                    () => {
                                        vm.$refs.contacts_datatable_user.vmDataTable.ajax.reload();
                                    },
                                    () => {}
                                );
                            },
                            (error) => {
                                // Note: The alert text seems to indicate to display the user name, but the name is not retrieved from the error response
                                swal.fire({
                                    title: 'Reinstate User',
                                    text:
                                        'There was an error reinstating ' +
                                        displayName +
                                        '. ' +
                                        helpers.apiVueResourceError(error),
                                    icon: 'error',
                                });
                            }
                        );
                } else if (action == 'make_admin_contact') {
                    helpers
                        .fetchUrl(
                            helpers.add_endpoint_json(
                                api_endpoints.organisations,
                                vm.org.id + '/make_admin_user'
                            ),
                            {
                                method: 'POST',
                                body: JSON.stringify(vm.contact_user),
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                            }
                        )
                        .then(
                            () => {
                                // Note: This block is missing a response to retrieve the name from
                                swal.fire({
                                    title: 'Organisation Admin',
                                    text:
                                        'You have successfully made ' +
                                        displayName +
                                        ' an Organisation Admin.',
                                    icon: 'success',
                                    confirmButtonText: 'OK',
                                }).then(
                                    () => {
                                        vm.$refs.contacts_datatable_user.vmDataTable.ajax.reload();
                                    },
                                    () => {}
                                );
                            },
                            (error) => {
                                // Note: The alert text seems to indicate to display the user name, but the name is not retrieved from the error response
                                swal.fire({
                                    title: 'Organisation Admin',
                                    text: error,
                                    icon: 'error',
                                });
                            }
                        );
                } else if (action == 'make_user_contact') {
                    helpers
                        .fetchUrl(
                            helpers.add_endpoint_json(
                                api_endpoints.organisations,
                                vm.org.id + '/make_user'
                            ),
                            {
                                method: 'POST',
                                body: JSON.stringify(vm.contact_user),
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                            }
                        )
                        .then(
                            () => {
                                // Note: This block is missing a response to retrieve the name from
                                swal.fire({
                                    title: 'Organisation User',
                                    text:
                                        'You have successfully made ' +
                                        displayName +
                                        ' an Organisation User.',
                                    icon: 'success',
                                    confirmButtonText: 'OK',
                                }).then(
                                    () => {
                                        vm.$refs.contacts_datatable_user.vmDataTable.ajax.reload();
                                        if (
                                            vm.contact_user.email ==
                                            vm.profile.email
                                        ) {
                                            this.$router.push('/external');
                                        }
                                    },
                                    () => {}
                                );
                            },
                            (error) => {
                                // Note: The alert text seems to indicate to display the user name, but the name is not retrieved from the error response
                                console.log(error);
                                var text = helpers.apiVueResourceError(error);
                                swal.fire({
                                    title: 'Company Admin',
                                    text: error,
                                    icon: 'error',
                                });
                            }
                        );
                } else if (action == 'accept') {
                    helpers
                        .fetchUrl(
                            helpers.add_endpoint_json(
                                api_endpoints.organisations,
                                vm.org.id + '/accept_user'
                            ),
                            {
                                method: 'POST',
                                body: JSON.stringify(vm.contact_user),
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                            }
                        )
                        .then(
                            () => {
                                // Note: This block is missing a response to retrieve the name from
                                swal.fire({
                                    title: 'Contact Accept',
                                    text:
                                        'You have successfully accepted ' +
                                        displayName +
                                        '.',
                                    icon: 'success',
                                    confirmButtonText: 'OK',
                                }).then(
                                    () => {
                                        vm.$refs.contacts_datatable_user.vmDataTable.ajax.reload();
                                    },
                                    () => {}
                                );
                            },
                            (error) => {
                                // Note: The alert text seems to indicate to display the user name, but the name is not retrieved from the error response
                                swal.fire({
                                    title: 'Contact Accept',
                                    text:
                                        'There was an error accepting ' +
                                        error +
                                        '.',
                                    icon: 'error',
                                });
                            }
                        );
                } else if (action == 'decline') {
                    helpers
                        .fetchUrl(
                            helpers.add_endpoint_json(
                                api_endpoints.organisations,
                                vm.org.id + '/decline_user'
                            ),
                            {
                                method: 'POST',
                                body: JSON.stringify(vm.contact_user),
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                            }
                        )
                        .then(
                            () => {
                                // Note: This block is missing a response to retrieve the name from
                                swal.fire({
                                    title: 'Contact Decline',
                                    text:
                                        'You have successfully declined ' +
                                        displayName +
                                        '.',
                                    icon: 'success',
                                    confirmButtonText: 'OK',
                                }).then(
                                    () => {
                                        vm.$refs.contacts_datatable_user.vmDataTable.ajax.reload();
                                    },
                                    () => {}
                                );
                            },
                            (error) => {
                                // Note: The alert text seems to indicate to display the user name, but the name is not retrieved from the error response
                                swal.fire({
                                    title: 'Contact Decline',
                                    text:
                                        'There was an error declining ' +
                                        error +
                                        '.',
                                    icon: 'error',
                                });
                            }
                        );
                } else if (action == 'accept_declined') {
                    helpers
                        .fetchUrl(
                            helpers.add_endpoint_json(
                                api_endpoints.organisations,
                                vm.org.id + '/accept_declined_user'
                            ),
                            {
                                method: 'POST',
                                body: JSON.stringify(vm.contact_user),
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                            }
                        )
                        .then(
                            () => {
                                // Note: This block is missing a response to retrieve the name from
                                swal.fire({
                                    title: 'Contact Accept (Previously Declined)',
                                    text:
                                        'You have successfully accepted ' +
                                        displayName +
                                        '.',
                                    icon: 'success',
                                    confirmButtonText: 'OK',
                                }).then(
                                    () => {
                                        vm.$refs.contacts_datatable_user.vmDataTable.ajax.reload();
                                    },
                                    () => {}
                                );
                            },
                            (error) => {
                                // Note: The alert text seems to indicate to display the user name, but the name is not retrieved from the error response
                                swal.fire({
                                    title: 'Contact Accept (Previously Declined)',
                                    text:
                                        'There was an error accepting ' +
                                        error +
                                        '.',
                                    icon: 'error',
                                });
                            }
                        );
                }
            }
        },
        shouldRequireCommsLog: function (action) {
            return (
                this.is_commercialoperator_admin &&
                (action === 'accept' || action === 'decline')
            );
        },
        triggerLinkedUserAction: function (action) {
            if (this.shouldRequireCommsLog(action)) {
                this.pendingCommsAction = action;
                if (!this.showAddCommsModal) {
                    this.showAddCommsModal = true;
                    this.$nextTick(() => {
                        if (this.$refs.add_comm_org_user_action) {
                            this.$refs.add_comm_org_user_action.isModalOpen = true;
                        }
                    });
                    return;
                }

                if (this.$refs.add_comm_org_user_action) {
                    this.$refs.add_comm_org_user_action.isModalOpen = true;
                }
                return;
            }

            this.orgAction(action);
        },
        handleCommsActionFromCommsLog: function (action) {
            const linkedUserAction = action || this.pendingCommsAction;
            this.pendingCommsAction = '';

            if (linkedUserAction) {
                this.orgAction(linkedUserAction);
            }
        },
        eventListeners: function () {
            const vm = this;

            vm.$refs.contacts_datatable_user.vmDataTable.on(
                'click',
                '.unlink_contact',
                (e) => {
                    e.preventDefault();
                    if (!vm.updateContactUser(e)) {
                        swal.fire({
                            title: 'Unlink',
                            text: 'Could not determine which user to unlink. Please try again.',
                            icon: 'error',
                        });
                        return;
                    }
                    const name = `${vm.contact_user.first_name} ${vm.contact_user.last_name}`;

                    swal.fire({
                        title: 'Unlink',
                        text:
                            'Are you sure you want to unlink ' +
                            name +
                            ' (' +
                            vm.contact_user.email +
                            ')?',
                        showCancelButton: true,
                        confirmButtonText: 'Accept',
                    }).then(
                        async (result) => {
                            if (!result.isConfirmed) {
                                return;
                            }
                            if (result) {
                                this.orgAction('unlink');
                            }
                        },
                        () => {}
                    );
                }
            );

            vm.$refs.contacts_datatable_user.vmDataTable.on(
                'click',
                '.reinstate_contact',
                (e) => {
                    e.preventDefault();
                    vm.updateContactUser(e);
                    const name = `${vm.contact_user.first_name} ${vm.contact_user.last_name}`;

                    swal.fire({
                        title: 'Reinstate User',
                        text:
                            'Are you sure you want to Reinstate  ' +
                            name +
                            ' (' +
                            vm.contact_user.email +
                            ')?',
                        showCancelButton: true,
                        confirmButtonText: 'Accept',
                    }).then(
                        (result) => {
                            if (!result.isConfirmed) {
                                return;
                            }
                            if (result) {
                                this.orgAction('reinstate');
                            }
                        },
                        () => {}
                    );
                }
            );

            vm.$refs.contacts_datatable_user.vmDataTable.on(
                'click',
                '.relink_contact',
                (e) => {
                    e.preventDefault();
                    vm.updateContactUser(e);
                    const name = `${vm.contact_user.first_name} ${vm.contact_user.last_name}`;

                    swal.fire({
                        title: 'Relink User',
                        text:
                            'Are you sure you want to relink  ' +
                            name +
                            ' (' +
                            vm.contact_user.email +
                            ')?',
                        showCancelButton: true,
                        confirmButtonText: 'Accept',
                    }).then(
                        (result) => {
                            if (result) {
                                if (!result.isConfirmed) {
                                    return;
                                }
                                this.orgAction('relink');
                            }
                        },
                        () => {}
                    );
                }
            );

            vm.$refs.contacts_datatable_user.vmDataTable.on(
                'click',
                '.suspend_contact',
                (e) => {
                    e.preventDefault();
                    vm.updateContactUser(e);
                    const name = `${vm.contact_user.first_name} ${vm.contact_user.last_name}`;

                    swal.fire({
                        title: 'Suspend User',
                        text:
                            'Are you sure you want to suspend  ' +
                            name +
                            ' (' +
                            vm.contact_user.email +
                            ')?',
                        showCancelButton: true,
                        confirmButtonText: 'Accept',
                    }).then(
                        (result) => {
                            if (result) {
                                if (!result.isConfirmed) {
                                    return;
                                }
                                this.orgAction('suspend');
                            }
                        },
                        () => {}
                    );
                }
            );

            vm.$refs.contacts_datatable_user.vmDataTable.on(
                'click',
                '.make_admin_contact',
                (e) => {
                    e.preventDefault();
                    vm.updateContactUser(e);
                    const name = `${vm.contact_user.first_name} ${vm.contact_user.last_name}`;

                    swal.fire({
                        title: 'Organisation Admin',
                        text:
                            'Are you sure you want to make ' +
                            name +
                            ' (' +
                            vm.contact_user.email +
                            ') an Organisation Admin?',
                        showCancelButton: true,
                        confirmButtonText: 'Accept',
                    }).then(
                        (result) => {
                            if (result) {
                                if (!result.isConfirmed) {
                                    return;
                                }
                                this.orgAction('make_admin_contact');
                            }
                        },
                        () => {}
                    );
                }
            );

            vm.$refs.contacts_datatable_user.vmDataTable.on(
                'click',
                '.make_user_contact',
                (e) => {
                    e.preventDefault();
                    vm.updateContactUser(e);
                    const name = `${vm.contact_user.first_name} ${vm.contact_user.last_name}`;

                    swal.fire({
                        title: 'Organisation User',
                        text:
                            'Are you sure you want to make ' +
                            name +
                            ' (' +
                            vm.contact_user.email +
                            ') an Organisation User?',
                        showCancelButton: true,
                        confirmButtonText: 'Accept',
                    }).then(
                        (result) => {
                            if (result) {
                                if (!result.isConfirmed) {
                                    return;
                                }
                                this.orgAction('make_user_contact');
                            }
                        },
                        () => {}
                    );
                }
            );

            vm.$refs.contacts_datatable_user.vmDataTable.on(
                'click',
                '.accept_contact',
                (e) => {
                    e.preventDefault();
                    vm.updateContactUser(e);
                    const name = `${vm.contact_user.first_name} ${vm.contact_user.last_name}`;

                    swal.fire({
                        title: 'Contact Accept',
                        text:
                            'Are you sure you want to accept contact request ' +
                            name +
                            ' (' +
                            vm.contact_user.email +
                            ')?',
                        showCancelButton: true,
                        confirmButtonText: 'Accept',
                    }).then(
                        (result) => {
                            if (result) {
                                if (!result.isConfirmed) {
                                    return;
                                }
                                this.triggerLinkedUserAction('accept');
                            }
                        },
                        () => {}
                    );
                }
            );

            vm.$refs.contacts_datatable_user.vmDataTable.on(
                'click',
                '.decline_contact',
                (e) => {
                    e.preventDefault();
                    vm.updateContactUser(e);
                    const name = `${vm.contact_user.first_name} ${vm.contact_user.last_name}`;

                    swal.fire({
                        title: 'Contact Decline',
                        text:
                            'Are you sure you want to decline the contact request for ' +
                            name +
                            ' (' +
                            vm.contact_user.email +
                            ')?',
                        showCancelButton: true,
                        confirmButtonText: 'Accept',
                    }).then(
                        (result) => {
                            if (result) {
                                if (!result.isConfirmed) {
                                    return;
                                }
                                this.triggerLinkedUserAction('decline');
                            }
                        },
                        () => {}
                    );
                }
            );

            vm.$refs.contacts_datatable_user.vmDataTable.on(
                'click',
                '.accept_declined_contact',
                (e) => {
                    e.preventDefault();
                    vm.updateContactUser(e);
                    const name = `${vm.contact_user.first_name} ${vm.contact_user.last_name}`;

                    swal.fire({
                        title: 'Contact Accept (Previously Declined)',
                        text:
                            'Are you sure you want to accept the previously declined contact request for ' +
                            name +
                            ' (' +
                            vm.contact_user.email +
                            ')?',
                        showCancelButton: true,
                        confirmButtonText: 'Accept',
                    }).then(
                        (result) => {
                            if (result) {
                                if (!result.isConfirmed) {
                                    return;
                                }
                                this.orgAction('accept_declined');
                            }
                        },
                        () => {}
                    );
                }
            );
        },
        fetchInitialData: function () {
            const vm = this;
            const orgId = vm.$route.params.org_id;
            let initialisers = [
                utils.fetchCountries().catch(() => []),
                utils.fetchLinkedOrganisation(orgId).catch(() => null),
                utils.fetchProfile().catch(() => ({
                    commercialoperator_organisations: [],
                })),
            ];
            return Promise.all(initialisers).then((data) => {
                vm.countries = data[0] || [];
                vm.org = data[1] || {};

                vm.profile = data[2] || {
                    commercialoperator_organisations: [],
                };
                vm.org.organisation_address =
                    vm.org.organisation_address != null
                        ? vm.org.organisation_address
                        : {};
                vm.org.pins = vm.org.pins != null ? vm.org.pins : {};
                vm.is_commercialoperator_admin =
                    vm.profile.is_commercialoperator_admin;
                vm.is_org_access_member = vm.profile.is_org_access_member;
                var profile_org = null;
                (vm.profile.commercialoperator_organisations || []).forEach(
                    (org) => {
                        if (org.id == vm.org.id) {
                            profile_org = org;
                        }
                    }
                );
                vm.is_org_admin = profile_org ? profile_org.is_admin : false;

                if (!vm.org || Object.keys(vm.org).length === 0) {
                    vm.org = {
                        organisation_address: {},
                        pins: {},
                        delegates: [],
                    };
                }

                if (!Array.isArray(vm.org.delegates)) {
                    vm.org.delegates = [];
                }

                if (
                    vm.contact_details_options_ref &&
                    vm.contact_details_options_ref.ajax &&
                    vm.contact_details_options_ref.ajax.url
                ) {
                    vm.contact_details_options_ref.ajax.url =
                        helpers.add_endpoint_json(
                            api_endpoints.organisations,
                            orgId + '/contacts_exclude'
                        );
                }

                if (
                    vm.contacts_options_ref &&
                    vm.contacts_options_ref.ajax &&
                    vm.contacts_options_ref.ajax.url
                ) {
                    vm.contacts_options_ref.ajax.url =
                        helpers.add_endpoint_json(
                            api_endpoints.organisations,
                            orgId + '/contacts_exclude'
                        );
                }

                vm.isContactDetailsTableReady = true;
                vm.$nextTick(() => {
                    vm.initialiseSectionLoaders();
                    vm.bindContactDetailsEditListener();
                });

                if (vm.$refs.contacts_datatable_user?.vmDataTable) {
                    vm.$refs.contacts_datatable_user.vmDataTable.ajax.reload();
                }

                return { success: true };
            });
        },
        updateContactUser: function (event) {
            const vm = this;
            const normalizeValue = (value) => {
                if (
                    value === undefined ||
                    value === null ||
                    value === 'undefined' ||
                    value === 'null'
                ) {
                    return '';
                }
                return value;
            };

            // With delegated events, click target can be an inner icon; always
            // resolve the nearest action element that carries data-* attributes.
            let $source = $(event.target).closest('[data-email]');
            if (!$source.length) {
                $source = $(event.target).closest('a, button');
            }
            if (!$source.length) {
                $source = $(event.target);
            }

            let firstname = normalizeValue($source.data('firstname'));
            let lastname = normalizeValue($source.data('lastname'));
            let email = normalizeValue($source.data('email'));
            let mobile = normalizeValue($source.data('mobile'));
            let phone = normalizeValue($source.data('phone'));

            if (!email || (!firstname && !lastname)) {
                const $row = $source.closest('tr');
                const $parentRow = $row.hasClass('child')
                    ? $row.prev('tr')
                    : $row;
                const rowData = vm.$refs.contacts_datatable_user?.vmDataTable
                    ?.row($parentRow)
                    .data();
                if (rowData) {
                    firstname = firstname || normalizeValue(rowData.first_name);
                    lastname = lastname || normalizeValue(rowData.last_name);
                    email = email || normalizeValue(rowData.email);
                    mobile = mobile || normalizeValue(rowData.mobile_number);
                    phone = phone || normalizeValue(rowData.phone_number);
                }
            }

            if (!email) {
                return false;
            }

            const new_user = {
                first_name: firstname,
                last_name: lastname,
                email: email,
                mobile_number: mobile,
                phone_number: phone,
            };

            this.contact_user = { ...new_user };
            return true;
        },
    },
};
</script>

<style scoped>
.btn-status {
    height: 28px;
}
</style>
