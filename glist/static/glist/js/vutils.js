
var sortHeader = {
    delimiters: ['${', '}'],
    template:
        '<a @click="sortIt" style="cursor: pointer"> '
        +    ' <slot></slot> '
        +    ' <small v-if="isSorted()" style="width: 0; overflow-x: visible" :class="\'text-info glyphicon glyphicon-circle-arrow-\' + (isAsc() ? \'down\': \'up\')"></small>'
        + ' </a>',
    props: ['colname'],
    methods: {
      sortIt: function (ev) {
        var self = this;
        self.$parent.sortBy(self.colname);
      },
      isSorted: function (e) {
        var self = this;
        return self.$parent.sortKeys.length && self.$parent.sortKeys[0] == self.colname || false
      },
      isAsc: function (e) {
        return this.$parent.sortWays.length &&  this.$parent.sortWays[0] == 'asc' || false
      }
    }
};

tableComponent = {
    data: function () {
        return {
            sortKey: '',
            sortWays: new Array(),
            sortKeys: new Array(),
            searchBox: '',
            searchFields: [],
            searchStrings: {},
        }
    },
    components: {
        'col-header': sortHeader
    },
    methods: {
        sortBy: function(sortKey, direction) {
            var self = this,
                found = self.sortKeys.indexOf(sortKey),
                dir = null;
            if ( found > -1) {
                if (found == 0) {
                    // just reverse the sorting order
                    dir = direction || (self.sortWays[found] == 'asc'? 'desc': 'asc');
                    self.sortWays[found] = dir
                } else {
                    // remove from previous sorts
                    self.sortKeys.splice(found, 1);
                    self.sortWays.splice(found, 1);
                    // and add anew
                    self.sortKeys.unshift(sortKey);
                    self.sortWays.unshift(direction || 'asc');
                }
            } else {
                self.sortKeys.unshift(sortKey);
                self.sortWays.unshift(direction || 'asc');
            }
            self.sortKey = sortKey;
            self.sortWays = self.sortWays.slice(0, self.sortWays.length);
        },
        orderedList: function(collection) {
            var self = this;
            if (self.sortKeys.length)
                return _.orderBy(collection, self.sortKeys, self.sortWays);
            else
                return collection
        },
        filteredList: function(collection, key) {
            var self = this,
                l = self.searchFields.length,
                lowSearch = self.searchBox.toLowerCase(),
                out;
            if (lowSearch.hasOwnProperty('trim'))
                lowSearch = lowSearch.trim();
            if (lowSearch.length > 1) {
                out = _.filter(collection, function(item){
                    var ss = self.searchStrings[item[key || 'id']];
                    return ss && ss.indexOf(lowSearch) > -1 // || false
                })
                return out
            } else
                return collection
        },
        updateIndex: function (obj, key) {
            var self = this,
                s = '',
                l = self.searchFields.length,
                val = '';
            key = key || 'id';
            for (var j=0; j<l; j++) {
                val = obj[self.searchFields[j]];
                if (typeof(val) == 'string')
                    s += val.toLowerCase() + ' '
            }
            self.searchStrings[obj[key]] = s;
        },
        indexList: function(collection, initSortKey, indexKey) {
            var self = this;
            // data does not change, all text, let's cache it and lowercase-it
            collection.forEach(function (o) {
                var key = indexKey || 'id';
                if (key)
                    self.updateIndex(o, key)
            })
            self.sortKeys = [initSortKey];
            self.sortWays = ['asc'];
        }
    }
}
